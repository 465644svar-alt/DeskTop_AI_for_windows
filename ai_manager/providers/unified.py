"""
Unified AI Providers with consistent interface
All providers inherit from HTTPAIProvider for common functionality
"""

import time
import logging
import requests
from typing import Dict, List, Tuple, Optional, Iterator

from .base import HTTPAIProvider, AIProvider, APIError, ErrorCategory

logger = logging.getLogger(__name__)


class OpenAIProvider(HTTPAIProvider):
    """OpenAI GPT provider"""

    AVAILABLE_MODELS = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "o1-preview",
        "o1-mini"
    ]

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini"):
        super().__init__("OpenAI GPT", api_key, "#10a37f", model)
        self.base_url = "https://api.openai.com/v1"
        self.max_context_tokens = 128000 if "gpt-4" in model else 16000
        self.system_prompt = "You are a helpful assistant."

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _build_request_data(self, messages: List[dict]) -> dict:
        # Add system prompt
        all_messages = [{"role": "system", "content": self.system_prompt}]
        all_messages.extend(messages)

        return {
            "model": self.model,
            "messages": all_messages,
            "max_tokens": self.max_response_tokens,
            "temperature": 0.7
        }

    def _parse_response(self, response: requests.Response) -> str:
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def query_stream(self, question: str) -> Iterator[Tuple[str, bool]]:
        """Stream query results"""
        if not self.api_key:
            yield f"Error: Enter {self.name} API key", True
            return

        self.add_to_history("user", question)

        try:
            headers = self._get_headers()
            data = self._build_request_data(self.conversation_history)
            data["stream"] = True

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                stream=True,
                timeout=self.timeout
            )

            if response.status_code != 200:
                raise self._parse_error(response)

            full_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        line = line[6:]
                        if line == "[DONE]":
                            break
                        try:
                            import json
                            chunk_data = json.loads(line)
                            delta = chunk_data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_response += content
                                yield content, False
                        except Exception:
                            pass

            self.add_to_history("assistant", full_response)
            yield "", True

        except Exception as e:
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                self.conversation_history.pop()
            yield f"Error: {str(e)}", True


class AnthropicProvider(HTTPAIProvider):
    """Anthropic Claude provider"""

    AVAILABLE_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ]

    def __init__(self, api_key: str = "", model: str = "claude-3-5-haiku-20241022"):
        super().__init__("Anthropic Claude", api_key, "#cc785c", model)
        self.base_url = "https://api.anthropic.com/v1"
        self.max_context_tokens = 200000

    def _get_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

    def _get_chat_endpoint(self) -> str:
        return "/messages"

    def _build_request_data(self, messages: List[dict]) -> dict:
        # Anthropic doesn't use system in messages array
        return {
            "model": self.model,
            "max_tokens": self.max_response_tokens,
            "messages": messages
        }

    def _parse_response(self, response: requests.Response) -> str:
        data = response.json()
        return data["content"][0]["text"]

    def query_stream(self, question: str) -> Iterator[Tuple[str, bool]]:
        """Stream query results"""
        if not self.api_key:
            yield f"Error: Enter {self.name} API key", True
            return

        self.add_to_history("user", question)

        try:
            headers = self._get_headers()
            data = self._build_request_data(self.conversation_history)
            data["stream"] = True

            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=data,
                stream=True,
                timeout=self.timeout
            )

            if response.status_code != 200:
                raise self._parse_error(response)

            full_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        try:
                            import json
                            event_data = json.loads(line[6:])
                            if event_data.get("type") == "content_block_delta":
                                content = event_data.get("delta", {}).get("text", "")
                                if content:
                                    full_response += content
                                    yield content, False
                        except Exception:
                            pass

            self.add_to_history("assistant", full_response)
            yield "", True

        except Exception as e:
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                self.conversation_history.pop()
            yield f"Error: {str(e)}", True


class GeminiProvider(HTTPAIProvider):
    """Google Gemini provider"""

    AVAILABLE_MODELS = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro"
    ]

    def __init__(self, api_key: str = "", model: str = "gemini-1.5-flash"):
        super().__init__("Google Gemini", api_key, "#4285f4", model)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.max_context_tokens = 1000000  # Gemini has huge context

    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    def _get_chat_endpoint(self) -> str:
        return f"/models/{self.model}:generateContent?key={self.api_key}"

    def _build_request_data(self, messages: List[dict]) -> dict:
        # Convert to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        return {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": self.max_response_tokens
            }
        }

    def _parse_response(self, response: requests.Response) -> str:
        data = response.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        raise APIError("No response from Gemini", ErrorCategory.UNKNOWN, provider=self.name)

    def _make_request(self, method: str, endpoint: str, headers: Dict[str, str],
                      data: Optional[dict] = None, timeout: Optional[int] = None,
                      stream: bool = False) -> requests.Response:
        """Override to handle Gemini's different URL structure"""
        url = f"{self.base_url}{endpoint}"
        timeout = timeout or self.timeout

        try:
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
            if response.status_code >= 400:
                raise self._parse_error(response)
            return response
        except APIError:
            raise
        except requests.exceptions.Timeout:
            raise APIError("Request timeout", ErrorCategory.NETWORK, provider=self.name)
        except Exception as e:
            raise APIError(str(e), ErrorCategory.UNKNOWN, provider=self.name)

    def test_connection(self) -> bool:
        if not self.api_key:
            self.is_connected = False
            return False
        try:
            headers = self._get_headers()
            data = {"contents": [{"parts": [{"text": "Hi"}]}]}
            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
            response = requests.post(url, headers=headers, json=data, timeout=15)
            self.is_connected = response.status_code == 200
            return self.is_connected
        except Exception:
            self.is_connected = False
            return False


class DeepSeekProvider(HTTPAIProvider):
    """DeepSeek provider"""

    AVAILABLE_MODELS = [
        "deepseek-chat",
        "deepseek-coder"
    ]

    def __init__(self, api_key: str = "", model: str = "deepseek-chat"):
        super().__init__("DeepSeek", api_key, "#5c6bc0", model)
        self.base_url = "https://api.deepseek.com/v1"
        self.max_context_tokens = 64000
        self.system_prompt = "You are a helpful assistant."

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _build_request_data(self, messages: List[dict]) -> dict:
        all_messages = [{"role": "system", "content": self.system_prompt}]
        all_messages.extend(messages)

        return {
            "model": self.model,
            "messages": all_messages,
            "max_tokens": self.max_response_tokens,
            "temperature": 0.7
        }

    def _parse_response(self, response: requests.Response) -> str:
        data = response.json()
        return data["choices"][0]["message"]["content"]


class GroqProvider(HTTPAIProvider):
    """Groq provider (fast inference)"""

    AVAILABLE_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]

    def __init__(self, api_key: str = "", model: str = "llama-3.3-70b-versatile"):
        super().__init__("Groq", api_key, "#f55036", model)
        self.base_url = "https://api.groq.com/openai/v1"
        self.max_context_tokens = 32000
        self.system_prompt = "You are a helpful assistant."

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _build_request_data(self, messages: List[dict]) -> dict:
        all_messages = [{"role": "system", "content": self.system_prompt}]
        all_messages.extend(messages)

        return {
            "model": self.model,
            "messages": all_messages,
            "max_tokens": self.max_response_tokens,
            "temperature": 0.7
        }

    def _parse_response(self, response: requests.Response) -> str:
        data = response.json()
        return data["choices"][0]["message"]["content"]


class MistralProvider(HTTPAIProvider):
    """Mistral AI provider"""

    AVAILABLE_MODELS = [
        "mistral-small-latest",
        "mistral-medium-latest",
        "mistral-large-latest",
        "open-mistral-7b",
        "open-mixtral-8x7b"
    ]

    def __init__(self, api_key: str = "", model: str = "mistral-small-latest"):
        super().__init__("Mistral AI", api_key, "#ff7000", model)
        self.base_url = "https://api.mistral.ai/v1"
        self.max_context_tokens = 32000

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _build_request_data(self, messages: List[dict]) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_response_tokens,
            "temperature": 0.7
        }

    def _parse_response(self, response: requests.Response) -> str:
        data = response.json()
        return data["choices"][0]["message"]["content"]


# Provider registry for dynamic creation
PROVIDER_REGISTRY = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider
}

# Provider display info
PROVIDER_INFO = {
    "openai": {
        "name": "OpenAI GPT",
        "color": "#10a37f",
        "url": "https://platform.openai.com/api-keys",
        "description": "GPT-4, GPT-3.5 models"
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "color": "#cc785c",
        "url": "https://console.anthropic.com/",
        "description": "Claude 3.5, Claude 3 models"
    },
    "gemini": {
        "name": "Google Gemini",
        "color": "#4285f4",
        "url": "https://aistudio.google.com/apikey",
        "description": "Gemini 1.5 Pro/Flash"
    },
    "deepseek": {
        "name": "DeepSeek",
        "color": "#5c6bc0",
        "url": "https://platform.deepseek.com/",
        "description": "DeepSeek Chat & Coder"
    },
    "groq": {
        "name": "Groq",
        "color": "#f55036",
        "url": "https://console.groq.com/keys",
        "description": "Llama, Mixtral (fast)"
    },
    "mistral": {
        "name": "Mistral AI",
        "color": "#ff7000",
        "url": "https://console.mistral.ai/api-keys/",
        "description": "Mistral models"
    }
}


def create_provider(provider_key: str, api_key: str = "", model: str = "") -> Optional[AIProvider]:
    """Create a provider instance by key"""
    if provider_key in PROVIDER_REGISTRY:
        provider_class = PROVIDER_REGISTRY[provider_key]
        if model:
            return provider_class(api_key, model)
        return provider_class(api_key)
    return None
