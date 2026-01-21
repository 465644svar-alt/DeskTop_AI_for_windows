"""
Helper utilities for AI Manager
- Token counting and estimation
- Text processing
"""

import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.info("tiktoken not available, using estimation")


class TokenCounter:
    """Token counter with tiktoken or estimation fallback"""

    # Average chars per token for different languages
    CHARS_PER_TOKEN = {
        "english": 4.0,
        "code": 3.5,
        "mixed": 3.0,
        "russian": 2.0,  # Cyrillic uses more tokens
        "chinese": 1.5
    }

    def __init__(self, model: str = "gpt-4"):
        self.model = model
        self._encoder = None

        if TIKTOKEN_AVAILABLE:
            try:
                self._encoder = tiktoken.encoding_for_model(model)
            except KeyError:
                try:
                    self._encoder = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    pass

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self._encoder:
            try:
                return len(self._encoder.encode(text))
            except Exception:
                pass
        return self._estimate_tokens(text)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count based on character analysis"""
        if not text:
            return 0

        # Detect language/content type
        cyrillic_ratio = len(re.findall(r'[а-яА-ЯёЁ]', text)) / max(len(text), 1)
        code_ratio = len(re.findall(r'[{}()\[\];=<>]', text)) / max(len(text), 1)

        if cyrillic_ratio > 0.3:
            chars_per_token = self.CHARS_PER_TOKEN["russian"]
        elif code_ratio > 0.1:
            chars_per_token = self.CHARS_PER_TOKEN["code"]
        else:
            chars_per_token = self.CHARS_PER_TOKEN["mixed"]

        return int(len(text) / chars_per_token) + 1

    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count total tokens in a list of messages"""
        total = 0
        for msg in messages:
            # Add overhead for message structure (~4 tokens per message)
            total += 4
            content = msg.get("content", "")
            total += self.count_tokens(content)
        return total

    def trim_messages_by_tokens(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        keep_system: bool = True
    ) -> List[Dict[str, str]]:
        """Trim messages to fit within token limit"""
        if not messages:
            return messages

        result = []
        current_tokens = 0

        # If keeping system message, add it first
        system_msg = None
        other_messages = []

        for msg in messages:
            if msg.get("role") == "system" and keep_system:
                system_msg = msg
            else:
                other_messages.append(msg)

        if system_msg:
            system_tokens = self.count_tokens(system_msg.get("content", "")) + 4
            current_tokens += system_tokens
            result.append(system_msg)

        # Add messages from newest to oldest until limit
        for msg in reversed(other_messages):
            msg_tokens = self.count_tokens(msg.get("content", "")) + 4
            if current_tokens + msg_tokens <= max_tokens:
                result.insert(1 if system_msg else 0, msg)
                current_tokens += msg_tokens
            else:
                break

        # Ensure at least the last user message is included
        if len(result) == (1 if system_msg else 0) and other_messages:
            result.append(other_messages[-1])

        return result


def estimate_tokens(text: str) -> int:
    """Quick token estimation without creating TokenCounter"""
    if not text:
        return 0

    # Simple estimation: ~4 chars per token for English, ~2 for Cyrillic
    cyrillic_count = len(re.findall(r'[а-яА-ЯёЁ]', text))
    other_count = len(text) - cyrillic_count

    return int(cyrillic_count / 2 + other_count / 4) + 1


def truncate_text(text: str, max_chars: int = 500, suffix: str = "...") -> str:
    """Truncate text to max characters"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - len(suffix)] + suffix


def format_elapsed_time(seconds: float) -> str:
    """Format elapsed time nicely"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"


def sanitize_filename(name: str) -> str:
    """Sanitize string for use as filename"""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name[:100]  # Limit length
