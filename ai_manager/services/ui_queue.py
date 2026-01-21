"""
Thread-safe UI Queue for Tkinter
Ensures all UI updates happen on the main thread
"""

from queue import Queue, Empty
from dataclasses import dataclass
from typing import Any, Callable, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of UI messages"""
    RESPONSE = "response"
    RESPONSE_CHUNK = "response_chunk"  # For streaming
    ERROR = "error"
    STATUS = "status"
    PROGRESS = "progress"
    FINISHED = "finished"
    CONNECTION_STATUS = "connection_status"
    CLEAR_CHAT = "clear_chat"
    METRICS_UPDATE = "metrics_update"


@dataclass
class UIMessage:
    """Message to be processed by UI thread"""
    msg_type: MessageType
    provider: str = ""
    data: Any = None
    elapsed: float = 0.0
    success: bool = True

    @classmethod
    def response(cls, provider: str, text: str, elapsed: float):
        return cls(MessageType.RESPONSE, provider, text, elapsed, True)

    @classmethod
    def response_chunk(cls, provider: str, chunk: str):
        """For streaming responses"""
        return cls(MessageType.RESPONSE_CHUNK, provider, chunk)

    @classmethod
    def error(cls, provider: str, error: str, elapsed: float = 0):
        return cls(MessageType.ERROR, provider, error, elapsed, False)

    @classmethod
    def status(cls, text: str):
        return cls(MessageType.STATUS, "", text)

    @classmethod
    def progress(cls, value: float):
        """Progress value 0.0 to 1.0, or -1 for indeterminate"""
        return cls(MessageType.PROGRESS, "", value)

    @classmethod
    def finished(cls, count: int, total_time: float, filepath: str = ""):
        return cls(MessageType.FINISHED, "", {"count": count, "time": total_time, "file": filepath})

    @classmethod
    def connection_status(cls, provider: str, connected: bool):
        return cls(MessageType.CONNECTION_STATUS, provider, connected)

    @classmethod
    def metrics_update(cls, provider: str, metrics: dict):
        return cls(MessageType.METRICS_UPDATE, provider, metrics)


class UIQueue:
    """Thread-safe queue for UI updates

    Usage:
        # In main app __init__:
        self.ui_queue = UIQueue()
        self.ui_queue.start_polling(self, self._handle_ui_message)

        # In worker threads:
        self.ui_queue.put(UIMessage.response("OpenAI", "Hello!", 1.5))

        # In main app:
        def _handle_ui_message(self, msg: UIMessage):
            if msg.msg_type == MessageType.RESPONSE:
                self._show_response(msg.provider, msg.data, msg.elapsed)
    """

    def __init__(self, poll_interval: int = 50):
        """
        Args:
            poll_interval: Milliseconds between queue checks
        """
        self._queue: Queue = Queue()
        self._poll_interval = poll_interval
        self._polling = False
        self._widget = None
        self._handler = None

    def put(self, message: UIMessage):
        """Put a message in the queue (thread-safe)"""
        self._queue.put(message)

    def get(self, timeout: float = 0) -> Optional[UIMessage]:
        """Get a message from the queue"""
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def start_polling(self, widget, handler: Callable[[UIMessage], None]):
        """Start polling the queue from the main thread

        Args:
            widget: Tkinter widget with .after() method
            handler: Function to call with each UIMessage
        """
        self._widget = widget
        self._handler = handler
        self._polling = True
        self._poll()

    def stop_polling(self):
        """Stop polling"""
        self._polling = False

    def _poll(self):
        """Poll the queue and process messages"""
        if not self._polling or self._widget is None:
            return

        # Process all available messages
        messages_processed = 0
        max_per_poll = 20  # Limit to prevent UI blocking

        while messages_processed < max_per_poll:
            try:
                message = self._queue.get_nowait()
                if self._handler:
                    try:
                        self._handler(message)
                    except Exception as e:
                        logger.error(f"Error handling UI message: {e}")
                messages_processed += 1
            except Empty:
                break

        # Schedule next poll
        if self._polling:
            self._widget.after(self._poll_interval, self._poll)

    def clear(self):
        """Clear all pending messages"""
        while True:
            try:
                self._queue.get_nowait()
            except Empty:
                break

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self._queue.empty()

    @property
    def size(self) -> int:
        """Get approximate queue size"""
        return self._queue.qsize()
