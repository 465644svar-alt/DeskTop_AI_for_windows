"""
Base AI Provider classes with improved error handling and retry logic
"""

import time
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Iterator, Any
from dataclasses import dataclass
from enum import Enum

from ..utils.helpers import TokenCounter, estimate_tokens

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of API errors"""
    AUTH = "authentication"
    RATE_LIMIT = "rate_limit"
    CONTEXT_LENGTH = "context_length"
    SERVER = "server_error"
    NETWORK = "network"
    INVALID_REQUEST = "invalid_request"
    UNKNOWN = "unknown"


@dataclass
class APIError(Exception):
    """Structured API error"""
    message: str
    category: ErrorCategory
    status_code: int = 0
    retryable: bool = False
    raw_response: str = ""
    provider: str = ""

    def __str__(self):
        return f"[{self.provider}] {self.category.value}: {self.message}"


class AIProvider(ABC):
    """Base class for AI providers"""

    # Available models for this provider
    AVAILABLE_MODELS: List[str] = []

    def __init__(
        self,
        name: str,
        api_key: str = "",
        color: str = "#3498db",
        model: str = ""
    ):
        self.name = name
        self.api_key = api_key
        self.color = color
        self.is_connected = False
        self.enabled = True

        # Model selection
        self.model = model or (self.AVAILABLE_MODELS[0] if self.AVAILABLE_MODELS else "")

        # Conversation history
        self.conversation_history: List[dict] = []
        self.context_summary: str = ""  # Summary of older trimmed messages

        # Token management
        self.max_context_tokens = 8000  # Default, override per provider
        self.max_response_tokens = 4000
        self._token_counter = TokenCounter(self.model)

    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to the API"""
        raise NotImplementedError

    @abstractmethod
    def query(self, question: str) -> Tuple[str, float]:
        """Send query and return (response, elapsed_time)"""
        raise NotImplementedError

    def query_stream(self, question: str) -> Iterator[Tuple[str, bool]]:
        """Stream query results, yields (chunk, is_final)"""
        # Default implementation - non-streaming
        response, _ = self.query(question)
        yield response, True

    def clear_history(self):
        """Clear conversation history and summary"""
        self.conversation_history = []
        self.context_summary = ""

    def add_to_history(self, role: str, content: str):
        """Add message to history with smart trimming (checkpoint summary)"""
        self.conversation_history.append({"role": role, "content": content})
        self._trim_history()

    def _trim_history(self):
        """Trim history with checkpoint summary to preserve context"""
        max_history_tokens = self.max_context_tokens - self.max_response_tokens - 500  # Buffer

        total_tokens = self._token_counter.count_messages_tokens(self.conversation_history)
        if total_tokens <= max_history_tokens:
            return

        # Create a checkpoint summary from older messages instead of just deleting them
        keep_count = max(1, len(self.conversation_history) // 2)
        to_summarize = self.conversation_history[:-keep_count]
        self.conversation_history = self.conversation_history[-keep_count:]

        summary_parts = []
        if self.context_summary:
            summary_parts.append(self.context_summary)
        for msg in to_summarize:
            text = msg["content"]
            if len(text) > 300:
                text = text[:300] + "..."
            summary_parts.append(f"[{msg['role']}]: {text}")

        self.context_summary = "\n".join(summary_parts)
        if len(self.context_summary) > 4000:
            self.context_summary = self.context_summary[-4000:]

    def get_messages_with_context(self) -> List[dict]:
        """Get conversation messages with context summary prepended"""
        messages = []
        if self.context_summary:
            messages.append({
                "role": "system",
                "content": f"Previous conversation context summary:\n{self.context_summary}"
            })
        messages.extend(self.conversation_history)
        return messages

    def get_history_tokens(self) -> int:
        """Get current token count of history"""
        return self._token_counter.count_messages_tokens(self.conversation_history)

    def set_model(self, model: str):
        """Change the model"""
        if model in self.AVAILABLE_MODELS or not self.AVAILABLE_MODELS:
            self.model = model
            self._token_counter = TokenCounter(model)


class HTTPAIProvider(AIProvider):
    """Base class for HTTP-based AI providers with common functionality"""

    # HTTP settings
    DEFAULT_TIMEOUT = 120
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # Exponential backoff

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = ""
        self.timeout = self.DEFAULT_TIMEOUT

    def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Dict[str, str],
        data: Optional[dict] = None,
        timeout: Optional[int] = None,
        stream: bool = False
    ) -> requests.Response:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        timeout = timeout or self.timeout

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, timeout=timeout)
                else:
                    response = requests.post(
                        url, headers=headers, json=data,
                        timeout=timeout, stream=stream
                    )

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", self.RETRY_DELAYS[attempt]))
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"[{self.name}] Rate limited, retrying in {retry_after}s...")
                        time.sleep(retry_after)
                        continue
                    raise self._parse_error(response)

                # Check for server errors (potentially transient)
                if response.status_code >= 500:
                    if attempt < self.MAX_RETRIES - 1:
                        delay = self.RETRY_DELAYS[attempt]
                        logger.warning(f"[{self.name}] Server error {response.status_code}, retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    raise self._parse_error(response)

                # Client errors - don't retry
                if response.status_code >= 400:
                    raise self._parse_error(response)

                return response

            except requests.exceptions.Timeout:
                last_error = APIError(
                    message="Request timeout",
                    category=ErrorCategory.NETWORK,
                    retryable=True,
                    provider=self.name
                )
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"[{self.name}] Timeout, retrying...")
                    time.sleep(self.RETRY_DELAYS[attempt])
                    continue

            except requests.exceptions.ConnectionError as e:
                last_error = APIError(
                    message=f"Connection error: {str(e)[:100]}",
                    category=ErrorCategory.NETWORK,
                    retryable=True,
                    provider=self.name
                )
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"[{self.name}] Connection error, retrying...")
                    time.sleep(self.RETRY_DELAYS[attempt])
                    continue

            except APIError:
                raise

            except Exception as e:
                last_error = APIError(
                    message=str(e),
                    category=ErrorCategory.UNKNOWN,
                    retryable=False,
                    provider=self.name
                )

        if last_error:
            raise last_error
        raise APIError("Max retries exceeded", ErrorCategory.UNKNOWN, provider=self.name)

    def _parse_error(self, response: requests.Response) -> APIError:
        """Parse error from response"""
        status_code = response.status_code
        raw_text = ""
        error_message = f"HTTP {status_code}"

        try:
            raw_text = response.text[:500]
            error_data = response.json()

            # Try common error formats
            if "error" in error_data:
                err = error_data["error"]
                if isinstance(err, dict):
                    error_message = err.get("message", str(err))
                else:
                    error_message = str(err)
            elif "message" in error_data:
                error_message = error_data["message"]
            elif "detail" in error_data:
                error_message = str(error_data["detail"])
        except Exception:
            error_message = raw_text[:200] if raw_text else f"HTTP {status_code}"

        # Categorize error
        category = ErrorCategory.UNKNOWN
        retryable = False

        if status_code == 401:
            category = ErrorCategory.AUTH
            error_message = "Invalid API key"
        elif status_code == 403:
            category = ErrorCategory.AUTH
            error_message = "Access denied - check API key permissions"
        elif status_code == 429:
            category = ErrorCategory.RATE_LIMIT
            error_message = "Rate limit exceeded"
            retryable = True
        elif status_code == 400:
            if "context" in error_message.lower() or "token" in error_message.lower():
                category = ErrorCategory.CONTEXT_LENGTH
                error_message = "Context length exceeded - try shorter messages"
            else:
                category = ErrorCategory.INVALID_REQUEST
        elif status_code >= 500:
            category = ErrorCategory.SERVER
            error_message = f"Server error ({status_code})"
            retryable = True

        return APIError(
            message=error_message,
            category=category,
            status_code=status_code,
            retryable=retryable,
            raw_response=raw_text,
            provider=self.name
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get default headers - override in subclasses"""
        return {
            "Content-Type": "application/json"
        }

    @abstractmethod
    def _build_request_data(self, messages: List[dict]) -> dict:
        """Build request data for the API - override in subclasses"""
        raise NotImplementedError

    @abstractmethod
    def _parse_response(self, response: requests.Response) -> str:
        """Parse response from the API - override in subclasses"""
        raise NotImplementedError

    def query(self, question: str) -> Tuple[str, float]:
        """Send query and return (response, elapsed_time)"""
        if not self.api_key:
            return f"Error: Enter {self.name} API key", 0

        # Add user message to history
        self.add_to_history("user", question)

        start_time = time.time()

        try:
            # Build request with context summary
            headers = self._get_headers()
            data = self._build_request_data(self.get_messages_with_context())

            # Make request
            response = self._make_request("POST", self._get_chat_endpoint(), headers, data)

            # Parse response
            assistant_response = self._parse_response(response)
            elapsed = time.time() - start_time

            # Add to history
            self.add_to_history("assistant", assistant_response)

            return assistant_response, elapsed

        except APIError as e:
            elapsed = time.time() - start_time
            # Remove the user message we added since the request failed
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                self.conversation_history.pop()
            return f"Error: {e.message}", elapsed

        except Exception as e:
            elapsed = time.time() - start_time
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                self.conversation_history.pop()
            logger.exception(f"[{self.name}] Unexpected error")
            return f"Error: {str(e)}", elapsed

    def _get_chat_endpoint(self) -> str:
        """Get the chat completion endpoint - override if needed"""
        return "/chat/completions"

    def test_connection(self) -> bool:
        """Test connection to the API"""
        if not self.api_key:
            self.is_connected = False
            return False

        try:
            # Simple test request
            headers = self._get_headers()
            data = self._build_request_data([{"role": "user", "content": "Hi"}])
            data["max_tokens"] = 5  # Minimal response

            self._make_request("POST", self._get_chat_endpoint(), headers, data, timeout=15)
            self.is_connected = True
            return True

        except Exception as e:
            logger.warning(f"[{self.name}] Connection test failed: {e}")
            self.is_connected = False
            return False
