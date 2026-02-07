# НАЗНАЧЕНИЕ ФАЙЛА: Сервис очереди UI-событий для безопасного обновления интерфейса из фоновых задач.
"""
Thread-safe UI Queue for Tkinter
Ensures all UI updates happen on the main thread
"""

from queue import Queue, Empty  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from dataclasses import dataclass  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from typing import Any, Callable, Optional  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from enum import Enum  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
import logging  # ПОЯСНЕНИЕ: импортируется модуль logging.

logger = logging.getLogger(__name__)  # ПОЯСНЕНИЕ: обновляется значение переменной logger.


# ЛОГИЧЕСКИЙ БЛОК: класс `MessageType(Enum)` — объединяет состояние и поведение подсистемы.
class MessageType(Enum):  # ПОЯСНЕНИЕ: объявляется класс MessageType.
    """Types of UI messages"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
    RESPONSE = "response"  # ПОЯСНЕНИЕ: обновляется значение переменной RESPONSE.
    RESPONSE_CHUNK = "response_chunk"  # For streaming  # ПОЯСНЕНИЕ: обновляется значение переменной RESPONSE_CHUNK.
    ERROR = "error"  # ПОЯСНЕНИЕ: обновляется значение переменной ERROR.
    STATUS = "status"  # ПОЯСНЕНИЕ: обновляется значение переменной STATUS.
    PROGRESS = "progress"  # ПОЯСНЕНИЕ: обновляется значение переменной PROGRESS.
    FINISHED = "finished"  # ПОЯСНЕНИЕ: обновляется значение переменной FINISHED.
    CONNECTION_STATUS = "connection_status"  # ПОЯСНЕНИЕ: обновляется значение переменной CONNECTION_STATUS.
    CLEAR_CHAT = "clear_chat"  # ПОЯСНЕНИЕ: обновляется значение переменной CLEAR_CHAT.
    METRICS_UPDATE = "metrics_update"  # ПОЯСНЕНИЕ: обновляется значение переменной METRICS_UPDATE.


@dataclass  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
# ЛОГИЧЕСКИЙ БЛОК: класс `UIMessage` — объединяет состояние и поведение подсистемы.
class UIMessage:  # ПОЯСНЕНИЕ: объявляется класс UIMessage.
    """Message to be processed by UI thread"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
    msg_type: MessageType  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    provider: str = ""  # ПОЯСНЕНИЕ: обновляется значение переменной provider: str.
    data: Any = None  # ПОЯСНЕНИЕ: обновляется значение переменной data: Any.
    elapsed: float = 0.0  # ПОЯСНЕНИЕ: обновляется значение переменной elapsed: float.
    success: bool = True  # ПОЯСНЕНИЕ: обновляется значение переменной success: bool.

    @classmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `response` — выполняет отдельный шаг бизнес-логики.
    def response(cls, provider: str, text: str, elapsed: float):  # ПОЯСНЕНИЕ: объявляется функция response с параметрами из сигнатуры.
        """Описание: функция `response`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return cls(MessageType.RESPONSE, provider, text, elapsed, True)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    @classmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `response_chunk` — выполняет отдельный шаг бизнес-логики.
    def response_chunk(cls, provider: str, chunk: str):  # ПОЯСНЕНИЕ: объявляется функция response_chunk с параметрами из сигнатуры.
        """For streaming responses"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return cls(MessageType.RESPONSE_CHUNK, provider, chunk)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    @classmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `error` — выполняет отдельный шаг бизнес-логики.
    def error(cls, provider: str, error: str, elapsed: float = 0):  # ПОЯСНЕНИЕ: объявляется функция error с параметрами из сигнатуры.
        """Описание: функция `error`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return cls(MessageType.ERROR, provider, error, elapsed, False)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    @classmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `status` — выполняет отдельный шаг бизнес-логики.
    def status(cls, text: str):  # ПОЯСНЕНИЕ: объявляется функция status с параметрами из сигнатуры.
        """Описание: функция `status`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return cls(MessageType.STATUS, "", text)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    @classmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `progress` — выполняет отдельный шаг бизнес-логики.
    def progress(cls, value: float):  # ПОЯСНЕНИЕ: объявляется функция progress с параметрами из сигнатуры.
        """Progress value 0.0 to 1.0, or -1 for indeterminate"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return cls(MessageType.PROGRESS, "", value)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    @classmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `finished` — выполняет отдельный шаг бизнес-логики.
    def finished(cls, count: int, total_time: float, filepath: str = ""):  # ПОЯСНЕНИЕ: объявляется функция finished с параметрами из сигнатуры.
        """Описание: функция `finished`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return cls(MessageType.FINISHED, "", {"count": count, "time": total_time, "file": filepath})  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    @classmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `connection_status` — выполняет отдельный шаг бизнес-логики.
    def connection_status(cls, provider: str, connected: bool):  # ПОЯСНЕНИЕ: объявляется функция connection_status с параметрами из сигнатуры.
        """Описание: функция `connection_status`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return cls(MessageType.CONNECTION_STATUS, provider, connected)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    @classmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `metrics_update` — выполняет отдельный шаг бизнес-логики.
    def metrics_update(cls, provider: str, metrics: dict):  # ПОЯСНЕНИЕ: объявляется функция metrics_update с параметрами из сигнатуры.
        """Описание: функция `metrics_update`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return cls(MessageType.METRICS_UPDATE, provider, metrics)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.


# ЛОГИЧЕСКИЙ БЛОК: класс `UIQueue` — объединяет состояние и поведение подсистемы.
class UIQueue:  # ПОЯСНЕНИЕ: объявляется класс UIQueue.
    """Thread-safe queue for UI updates

    Usage:
        # In main app __init__:
        self.ui_queue = UIQueue()
        self.ui_queue.start_polling(self, self._handle_ui_message)

        # In worker threads:
        self.ui_queue.put(UIMessage.response("OpenAI", "Hello!", 1.5))

        # In main app:
        # ЛОГИЧЕСКИЙ БЛОК: функция `_handle_ui_message` — выполняет отдельный шаг бизнес-логики.
        def _handle_ui_message(self, msg: UIMessage):
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if msg.msg_type == MessageType.RESPONSE:
                self._show_response(msg.provider, msg.data, msg.elapsed)
    """

    # ЛОГИЧЕСКИЙ БЛОК: функция `__init__` — выполняет отдельный шаг бизнес-логики.
    def __init__(self, poll_interval: int = 50):  # ПОЯСНЕНИЕ: объявляется функция __init__ с параметрами из сигнатуры.
        """
        Args:
            poll_interval: Milliseconds between queue checks
        """
        self._queue: Queue = Queue()  # ПОЯСНЕНИЕ: обновляется значение переменной self._queue: Queue.
        self._poll_interval = poll_interval  # ПОЯСНЕНИЕ: обновляется значение переменной self._poll_interval.
        self._polling = False  # ПОЯСНЕНИЕ: обновляется значение переменной self._polling.
        self._widget = None  # ПОЯСНЕНИЕ: обновляется значение переменной self._widget.
        self._handler = None  # ПОЯСНЕНИЕ: обновляется значение переменной self._handler.

    # ЛОГИЧЕСКИЙ БЛОК: функция `put` — выполняет отдельный шаг бизнес-логики.
    def put(self, message: UIMessage):  # ПОЯСНЕНИЕ: объявляется функция put с параметрами из сигнатуры.
        """Put a message in the queue (thread-safe)"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self._queue.put(message)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get` — выполняет отдельный шаг бизнес-логики.
    def get(self, timeout: float = 0) -> Optional[UIMessage]:  # ПОЯСНЕНИЕ: объявляется функция get с параметрами из сигнатуры.
        """Get a message from the queue"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            return self._queue.get(timeout=timeout)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Empty:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `start_polling` — выполняет отдельный шаг бизнес-логики.
    def start_polling(self, widget, handler: Callable[[UIMessage], None]):  # ПОЯСНЕНИЕ: объявляется функция start_polling с параметрами из сигнатуры.
        """Start polling the queue from the main thread

        Args:
            widget: Tkinter widget with .after() method
            handler: Function to call with each UIMessage
        """
        self._widget = widget  # ПОЯСНЕНИЕ: обновляется значение переменной self._widget.
        self._handler = handler  # ПОЯСНЕНИЕ: обновляется значение переменной self._handler.
        self._polling = True  # ПОЯСНЕНИЕ: обновляется значение переменной self._polling.
        self._poll()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `stop_polling` — выполняет отдельный шаг бизнес-логики.
    def stop_polling(self):  # ПОЯСНЕНИЕ: объявляется функция stop_polling с параметрами из сигнатуры.
        """Stop polling"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self._polling = False  # ПОЯСНЕНИЕ: обновляется значение переменной self._polling.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_poll` — выполняет отдельный шаг бизнес-логики.
    def _poll(self):  # ПОЯСНЕНИЕ: объявляется функция _poll с параметрами из сигнатуры.
        """Poll the queue and process messages"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not self._polling or self._widget is None:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # Process all available messages
        messages_processed = 0  # ПОЯСНЕНИЕ: обновляется значение переменной messages_processed.
        max_per_poll = 20  # Limit to prevent UI blocking  # ПОЯСНЕНИЕ: обновляется значение переменной max_per_poll.

        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        while messages_processed < max_per_poll:  # ПОЯСНЕНИЕ: запускается цикл while до изменения условия.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                message = self._queue.get_nowait()  # ПОЯСНЕНИЕ: обновляется значение переменной message.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if self._handler:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                    try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                        self._handler(message)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                    except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                        logger.error(f"Error handling UI message: {e}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                messages_processed += 1  # ПОЯСНЕНИЕ: обновляется значение переменной messages_processed +.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except Empty:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                break  # ПОЯСНЕНИЕ: цикл прерывается немедленно.

        # Schedule next poll
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if self._polling:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self._widget.after(self._poll_interval, self._poll)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `clear` — выполняет отдельный шаг бизнес-логики.
    def clear(self):  # ПОЯСНЕНИЕ: объявляется функция clear с параметрами из сигнатуры.
        """Clear all pending messages"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        while True:  # ПОЯСНЕНИЕ: запускается цикл while до изменения условия.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                self._queue.get_nowait()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except Empty:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                break  # ПОЯСНЕНИЕ: цикл прерывается немедленно.

    @property  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `is_empty` — выполняет отдельный шаг бизнес-логики.
    def is_empty(self) -> bool:  # ПОЯСНЕНИЕ: объявляется функция is_empty с параметрами из сигнатуры.
        """Check if queue is empty"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return self._queue.empty()  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    @property  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `size` — выполняет отдельный шаг бизнес-логики.
    def size(self) -> int:  # ПОЯСНЕНИЕ: объявляется функция size с параметрами из сигнатуры.
        """Get approximate queue size"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return self._queue.qsize()  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
