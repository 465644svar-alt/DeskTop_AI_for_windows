# НАЗНАЧЕНИЕ ФАЙЛА: Базовые абстракции провайдеров ИИ: интерфейсы, общие структуры и контракты.
"""
Base AI Provider classes with improved error handling and retry logic
"""

import time  # ПОЯСНЕНИЕ: импортируется модуль time.
import logging  # ПОЯСНЕНИЕ: импортируется модуль logging.
import requests  # ПОЯСНЕНИЕ: импортируется модуль requests.
from abc import ABC, abstractmethod  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from typing import Dict, List, Tuple, Optional, Iterator, Any  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from dataclasses import dataclass  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from enum import Enum  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.

from ..utils.helpers import TokenCounter, estimate_tokens  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.

logger = logging.getLogger(__name__)  # ПОЯСНЕНИЕ: обновляется значение переменной logger.


# ЛОГИЧЕСКИЙ БЛОК: класс `ErrorCategory(Enum)` — объединяет состояние и поведение подсистемы.
class ErrorCategory(Enum):  # ПОЯСНЕНИЕ: объявляется класс ErrorCategory.
    """Categories of API errors"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
    AUTH = "authentication"  # ПОЯСНЕНИЕ: обновляется значение переменной AUTH.
    RATE_LIMIT = "rate_limit"  # ПОЯСНЕНИЕ: обновляется значение переменной RATE_LIMIT.
    CONTEXT_LENGTH = "context_length"  # ПОЯСНЕНИЕ: обновляется значение переменной CONTEXT_LENGTH.
    SERVER = "server_error"  # ПОЯСНЕНИЕ: обновляется значение переменной SERVER.
    NETWORK = "network"  # ПОЯСНЕНИЕ: обновляется значение переменной NETWORK.
    INVALID_REQUEST = "invalid_request"  # ПОЯСНЕНИЕ: обновляется значение переменной INVALID_REQUEST.
    UNKNOWN = "unknown"  # ПОЯСНЕНИЕ: обновляется значение переменной UNKNOWN.


@dataclass  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
# ЛОГИЧЕСКИЙ БЛОК: класс `APIError(Exception)` — объединяет состояние и поведение подсистемы.
class APIError(Exception):  # ПОЯСНЕНИЕ: объявляется класс APIError.
    """Structured API error"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
    message: str  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    category: ErrorCategory  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    status_code: int = 0  # ПОЯСНЕНИЕ: обновляется значение переменной status_code: int.
    retryable: bool = False  # ПОЯСНЕНИЕ: обновляется значение переменной retryable: bool.
    raw_response: str = ""  # ПОЯСНЕНИЕ: обновляется значение переменной raw_response: str.
    provider: str = ""  # ПОЯСНЕНИЕ: обновляется значение переменной provider: str.

    # ЛОГИЧЕСКИЙ БЛОК: функция `__str__` — выполняет отдельный шаг бизнес-логики.
    def __str__(self):  # ПОЯСНЕНИЕ: объявляется функция __str__ с параметрами из сигнатуры.
        """Описание: функция `__str__`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return f"[{self.provider}] {self.category.value}: {self.message}"  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.


# ЛОГИЧЕСКИЙ БЛОК: класс `AIProvider(ABC)` — объединяет состояние и поведение подсистемы.
class AIProvider(ABC):  # ПОЯСНЕНИЕ: объявляется класс AIProvider.
    """Base class for AI providers"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.

    # Available models for this provider
    AVAILABLE_MODELS: List[str] = []  # ПОЯСНЕНИЕ: обновляется значение переменной AVAILABLE_MODELS: List[str].

    # ЛОГИЧЕСКИЙ БЛОК: функция `__init__` — выполняет отдельный шаг бизнес-логики.
    def __init__(  # ПОЯСНЕНИЕ: объявляется функция __init__ с параметрами из сигнатуры.
        self,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        name: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        api_key: str = "",  # ПОЯСНЕНИЕ: обновляется значение переменной api_key: str.
        color: str = "#3498db",  # ПОЯСНЕНИЕ: обновляется значение переменной color: str.
        model: str = ""  # ПОЯСНЕНИЕ: обновляется значение переменной model: str.
    ):  # ПОЯСНЕНИЕ: начинается новый логический блок кода.
        """Описание: функция `__init__`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.name = name  # ПОЯСНЕНИЕ: обновляется значение переменной self.name.
        self.api_key = api_key  # ПОЯСНЕНИЕ: обновляется значение переменной self.api_key.
        self.color = color  # ПОЯСНЕНИЕ: обновляется значение переменной self.color.
        self.is_connected = False  # ПОЯСНЕНИЕ: обновляется значение переменной self.is_connected.
        self.enabled = True  # ПОЯСНЕНИЕ: обновляется значение переменной self.enabled.

        # Model selection
        self.model = model or (self.AVAILABLE_MODELS[0] if self.AVAILABLE_MODELS else "")  # ПОЯСНЕНИЕ: обновляется значение переменной self.model.

        # Conversation history
        self.conversation_history: List[dict] = []  # ПОЯСНЕНИЕ: обновляется значение переменной self.conversation_history: List[dict].

        # Token management
        self.max_context_tokens = 8000  # Default, override per provider  # ПОЯСНЕНИЕ: обновляется значение переменной self.max_context_tokens.
        self.max_response_tokens = 4000  # ПОЯСНЕНИЕ: обновляется значение переменной self.max_response_tokens.
        self._token_counter = TokenCounter(self.model)  # ПОЯСНЕНИЕ: обновляется значение переменной self._token_counter.

    @abstractmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `test_connection` — выполняет отдельный шаг бизнес-логики.
    def test_connection(self) -> bool:  # ПОЯСНЕНИЕ: объявляется функция test_connection с параметрами из сигнатуры.
        """Test connection to the API"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        raise NotImplementedError  # ПОЯСНЕНИЕ: генерируется исключение для обработки ошибки.

    @abstractmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `query` — выполняет отдельный шаг бизнес-логики.
    def query(self, question: str) -> Tuple[str, float]:  # ПОЯСНЕНИЕ: объявляется функция query с параметрами из сигнатуры.
        """Send query and return (response, elapsed_time)"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        raise NotImplementedError  # ПОЯСНЕНИЕ: генерируется исключение для обработки ошибки.

    # ЛОГИЧЕСКИЙ БЛОК: функция `query_stream` — выполняет отдельный шаг бизнес-логики.
    def query_stream(self, question: str) -> Iterator[Tuple[str, bool]]:  # ПОЯСНЕНИЕ: объявляется функция query_stream с параметрами из сигнатуры.
        """Stream query results, yields (chunk, is_final)"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # Default implementation - non-streaming
        response, _ = self.query(question)  # ПОЯСНЕНИЕ: обновляется значение переменной response, _.
        yield response, True  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `clear_history` — выполняет отдельный шаг бизнес-логики.
    def clear_history(self):  # ПОЯСНЕНИЕ: объявляется функция clear_history с параметрами из сигнатуры.
        """Clear conversation history"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.conversation_history = []  # ПОЯСНЕНИЕ: обновляется значение переменной self.conversation_history.

    # ЛОГИЧЕСКИЙ БЛОК: функция `add_to_history` — выполняет отдельный шаг бизнес-логики.
    def add_to_history(self, role: str, content: str):  # ПОЯСНЕНИЕ: объявляется функция add_to_history с параметрами из сигнатуры.
        """Add message to history with token-based trimming"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.conversation_history.append({"role": role, "content": content})  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self._trim_history()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_trim_history` — выполняет отдельный шаг бизнес-логики.
    def _trim_history(self):  # ПОЯСНЕНИЕ: объявляется функция _trim_history с параметрами из сигнатуры.
        """Trim history to fit within token limit"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        max_history_tokens = self.max_context_tokens - self.max_response_tokens - 500  # Buffer  # ПОЯСНЕНИЕ: обновляется значение переменной max_history_tokens.

        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        while len(self.conversation_history) > 1:  # ПОЯСНЕНИЕ: запускается цикл while до изменения условия.
            total_tokens = self._token_counter.count_messages_tokens(self.conversation_history)  # ПОЯСНЕНИЕ: обновляется значение переменной total_tokens.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if total_tokens <= max_history_tokens:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                break  # ПОЯСНЕНИЕ: цикл прерывается немедленно.
            # Remove oldest message (keep at least the last one)
            self.conversation_history.pop(0)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get_history_tokens` — выполняет отдельный шаг бизнес-логики.
    def get_history_tokens(self) -> int:  # ПОЯСНЕНИЕ: объявляется функция get_history_tokens с параметрами из сигнатуры.
        """Get current token count of history"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return self._token_counter.count_messages_tokens(self.conversation_history)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `set_model` — выполняет отдельный шаг бизнес-логики.
    def set_model(self, model: str):  # ПОЯСНЕНИЕ: объявляется функция set_model с параметрами из сигнатуры.
        """Change the model"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if model is not None:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.model = model  # ПОЯСНЕНИЕ: обновляется значение переменной self.model.
            self._token_counter = TokenCounter(model)  # ПОЯСНЕНИЕ: обновляется значение переменной self._token_counter.


# ЛОГИЧЕСКИЙ БЛОК: класс `HTTPAIProvider(AIProvider)` — объединяет состояние и поведение подсистемы.
class HTTPAIProvider(AIProvider):  # ПОЯСНЕНИЕ: объявляется класс HTTPAIProvider.
    """Base class for HTTP-based AI providers with common functionality"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.

    # HTTP settings
    DEFAULT_TIMEOUT = 120  # ПОЯСНЕНИЕ: обновляется значение переменной DEFAULT_TIMEOUT.
    MAX_RETRIES = 3  # ПОЯСНЕНИЕ: обновляется значение переменной MAX_RETRIES.
    RETRY_DELAYS = [1, 2, 4]  # Exponential backoff  # ПОЯСНЕНИЕ: обновляется значение переменной RETRY_DELAYS.

    # ЛОГИЧЕСКИЙ БЛОК: функция `__init__` — выполняет отдельный шаг бизнес-логики.
    def __init__(self, *args, **kwargs):  # ПОЯСНЕНИЕ: объявляется функция __init__ с параметрами из сигнатуры.
        """Описание: функция `__init__`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        super().__init__(*args, **kwargs)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.base_url = ""  # ПОЯСНЕНИЕ: обновляется значение переменной self.base_url.
        self.timeout = self.DEFAULT_TIMEOUT  # ПОЯСНЕНИЕ: обновляется значение переменной self.timeout.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_make_request` — выполняет отдельный шаг бизнес-логики.
    def _make_request(  # ПОЯСНЕНИЕ: объявляется функция _make_request с параметрами из сигнатуры.
        self,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        method: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        endpoint: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        headers: Dict[str, str],  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        data: Optional[dict] = None,  # ПОЯСНЕНИЕ: обновляется значение переменной data: Optional[dict].
        timeout: Optional[int] = None,  # ПОЯСНЕНИЕ: обновляется значение переменной timeout: Optional[int].
        stream: bool = False  # ПОЯСНЕНИЕ: обновляется значение переменной stream: bool.
    ) -> requests.Response:  # ПОЯСНЕНИЕ: начинается новый логический блок кода.
        """Make HTTP request with retry logic"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        url = f"{self.base_url}{endpoint}"  # ПОЯСНЕНИЕ: обновляется значение переменной url.
        timeout = timeout or self.timeout  # ПОЯСНЕНИЕ: обновляется значение переменной timeout.

        last_error = None  # ПОЯСНЕНИЕ: обновляется значение переменной last_error.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for attempt in range(self.MAX_RETRIES):  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if method.upper() == "GET":  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    response = requests.get(url, headers=headers, timeout=timeout)  # ПОЯСНЕНИЕ: обновляется значение переменной response.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                else:  # ПОЯСНЕНИЕ: выполняется альтернативная ветка else.
                    response = requests.post(  # ПОЯСНЕНИЕ: обновляется значение переменной response.
                        url, headers=headers, json=data,  # ПОЯСНЕНИЕ: обновляется значение переменной url, headers.
                        timeout=timeout, stream=stream  # ПОЯСНЕНИЕ: обновляется значение переменной timeout.
                    )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

                # Check for rate limiting
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if response.status_code == 429:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    retry_after = int(response.headers.get("Retry-After", self.RETRY_DELAYS[attempt]))  # ПОЯСНЕНИЕ: обновляется значение переменной retry_after.
                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    if attempt < self.MAX_RETRIES - 1:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                        logger.warning(f"[{self.name}] Rate limited, retrying in {retry_after}s...")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        time.sleep(retry_after)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        continue  # ПОЯСНЕНИЕ: переход к следующей итерации цикла.
                    raise self._parse_error(response)  # ПОЯСНЕНИЕ: генерируется исключение для обработки ошибки.

                # Check for server errors (potentially transient)
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if response.status_code >= 500:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    if attempt < self.MAX_RETRIES - 1:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                        delay = self.RETRY_DELAYS[attempt]  # ПОЯСНЕНИЕ: обновляется значение переменной delay.
                        logger.warning(f"[{self.name}] Server error {response.status_code}, retrying in {delay}s...")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        time.sleep(delay)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        continue  # ПОЯСНЕНИЕ: переход к следующей итерации цикла.
                    raise self._parse_error(response)  # ПОЯСНЕНИЕ: генерируется исключение для обработки ошибки.

                # Client errors - don't retry
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if response.status_code >= 400:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    raise self._parse_error(response)  # ПОЯСНЕНИЕ: генерируется исключение для обработки ошибки.

                return response  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except requests.exceptions.Timeout:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                last_error = APIError(  # ПОЯСНЕНИЕ: обновляется значение переменной last_error.
                    message="Request timeout",  # ПОЯСНЕНИЕ: обновляется значение переменной message.
                    category=ErrorCategory.NETWORK,  # ПОЯСНЕНИЕ: обновляется значение переменной category.
                    retryable=True,  # ПОЯСНЕНИЕ: обновляется значение переменной retryable.
                    provider=self.name  # ПОЯСНЕНИЕ: обновляется значение переменной provider.
                )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if attempt < self.MAX_RETRIES - 1:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    logger.warning(f"[{self.name}] Timeout, retrying...")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    time.sleep(self.RETRY_DELAYS[attempt])  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    continue  # ПОЯСНЕНИЕ: переход к следующей итерации цикла.

            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except requests.exceptions.ConnectionError as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                last_error = APIError(  # ПОЯСНЕНИЕ: обновляется значение переменной last_error.
                    message=f"Connection error: {str(e)[:100]}",  # ПОЯСНЕНИЕ: обновляется значение переменной message.
                    category=ErrorCategory.NETWORK,  # ПОЯСНЕНИЕ: обновляется значение переменной category.
                    retryable=True,  # ПОЯСНЕНИЕ: обновляется значение переменной retryable.
                    provider=self.name  # ПОЯСНЕНИЕ: обновляется значение переменной provider.
                )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if attempt < self.MAX_RETRIES - 1:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    logger.warning(f"[{self.name}] Connection error, retrying...")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    time.sleep(self.RETRY_DELAYS[attempt])  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    continue  # ПОЯСНЕНИЕ: переход к следующей итерации цикла.

            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except APIError:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                raise  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                last_error = APIError(  # ПОЯСНЕНИЕ: обновляется значение переменной last_error.
                    message=str(e),  # ПОЯСНЕНИЕ: обновляется значение переменной message.
                    category=ErrorCategory.UNKNOWN,  # ПОЯСНЕНИЕ: обновляется значение переменной category.
                    retryable=False,  # ПОЯСНЕНИЕ: обновляется значение переменной retryable.
                    provider=self.name  # ПОЯСНЕНИЕ: обновляется значение переменной provider.
                )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if last_error:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            raise last_error  # ПОЯСНЕНИЕ: генерируется исключение для обработки ошибки.
        raise APIError("Max retries exceeded", ErrorCategory.UNKNOWN, provider=self.name)  # ПОЯСНЕНИЕ: генерируется исключение для обработки ошибки.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_parse_error` — выполняет отдельный шаг бизнес-логики.
    def _parse_error(self, response: requests.Response) -> APIError:  # ПОЯСНЕНИЕ: объявляется функция _parse_error с параметрами из сигнатуры.
        """Parse error from response"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        status_code = response.status_code  # ПОЯСНЕНИЕ: обновляется значение переменной status_code.
        raw_text = ""  # ПОЯСНЕНИЕ: обновляется значение переменной raw_text.
        error_message = f"HTTP {status_code}"  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.

        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            raw_text = response.text[:500]  # ПОЯСНЕНИЕ: обновляется значение переменной raw_text.
            error_data = response.json()  # ПОЯСНЕНИЕ: обновляется значение переменной error_data.

            # Try common error formats
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if "error" in error_data:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                err = error_data["error"]  # ПОЯСНЕНИЕ: обновляется значение переменной err.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if isinstance(err, dict):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    error_message = err.get("message", str(err))  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                else:  # ПОЯСНЕНИЕ: выполняется альтернативная ветка else.
                    error_message = str(err)  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            elif "message" in error_data:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
                error_message = error_data["message"]  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            elif "detail" in error_data:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
                error_message = str(error_data["detail"])  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            error_message = raw_text[:200] if raw_text else f"HTTP {status_code}"  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.

        # Categorize error
        category = ErrorCategory.UNKNOWN  # ПОЯСНЕНИЕ: обновляется значение переменной category.
        retryable = False  # ПОЯСНЕНИЕ: обновляется значение переменной retryable.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if status_code == 401:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            category = ErrorCategory.AUTH  # ПОЯСНЕНИЕ: обновляется значение переменной category.
            error_message = "Invalid API key"  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        elif status_code == 403:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
            category = ErrorCategory.AUTH  # ПОЯСНЕНИЕ: обновляется значение переменной category.
            error_message = "Access denied - check API key permissions"  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        elif status_code == 429:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
            category = ErrorCategory.RATE_LIMIT  # ПОЯСНЕНИЕ: обновляется значение переменной category.
            error_message = "Rate limit exceeded"  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.
            retryable = True  # ПОЯСНЕНИЕ: обновляется значение переменной retryable.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        elif status_code == 400:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if "context" in error_message.lower() or "token" in error_message.lower():  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                category = ErrorCategory.CONTEXT_LENGTH  # ПОЯСНЕНИЕ: обновляется значение переменной category.
                error_message = "Context length exceeded - try shorter messages"  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            else:  # ПОЯСНЕНИЕ: выполняется альтернативная ветка else.
                category = ErrorCategory.INVALID_REQUEST  # ПОЯСНЕНИЕ: обновляется значение переменной category.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        elif status_code >= 500:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
            category = ErrorCategory.SERVER  # ПОЯСНЕНИЕ: обновляется значение переменной category.
            error_message = f"Server error ({status_code})"  # ПОЯСНЕНИЕ: обновляется значение переменной error_message.
            retryable = True  # ПОЯСНЕНИЕ: обновляется значение переменной retryable.

        return APIError(  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
            message=error_message,  # ПОЯСНЕНИЕ: обновляется значение переменной message.
            category=category,  # ПОЯСНЕНИЕ: обновляется значение переменной category.
            status_code=status_code,  # ПОЯСНЕНИЕ: обновляется значение переменной status_code.
            retryable=retryable,  # ПОЯСНЕНИЕ: обновляется значение переменной retryable.
            raw_response=raw_text,  # ПОЯСНЕНИЕ: обновляется значение переменной raw_response.
            provider=self.name  # ПОЯСНЕНИЕ: обновляется значение переменной provider.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_get_headers` — выполняет отдельный шаг бизнес-логики.
    def _get_headers(self) -> Dict[str, str]:  # ПОЯСНЕНИЕ: объявляется функция _get_headers с параметрами из сигнатуры.
        """Get default headers - override in subclasses"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return {  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
            "Content-Type": "application/json"  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        }  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    @abstractmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `_build_request_data` — выполняет отдельный шаг бизнес-логики.
    def _build_request_data(self, messages: List[dict]) -> dict:  # ПОЯСНЕНИЕ: объявляется функция _build_request_data с параметрами из сигнатуры.
        """Build request data for the API - override in subclasses"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        raise NotImplementedError  # ПОЯСНЕНИЕ: генерируется исключение для обработки ошибки.

    @abstractmethod  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `_parse_response` — выполняет отдельный шаг бизнес-логики.
    def _parse_response(self, response: requests.Response) -> str:  # ПОЯСНЕНИЕ: объявляется функция _parse_response с параметрами из сигнатуры.
        """Parse response from the API - override in subclasses"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        raise NotImplementedError  # ПОЯСНЕНИЕ: генерируется исключение для обработки ошибки.

    # ЛОГИЧЕСКИЙ БЛОК: функция `query` — выполняет отдельный шаг бизнес-логики.
    def query(self, question: str) -> Tuple[str, float]:  # ПОЯСНЕНИЕ: объявляется функция query с параметрами из сигнатуры.
        """Send query and return (response, elapsed_time)"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not self.api_key:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return f"Error: Enter {self.name} API key", 0  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # Add user message to history
        self.add_to_history("user", question)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        start_time = time.time()  # ПОЯСНЕНИЕ: обновляется значение переменной start_time.

        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            # Build request
            headers = self._get_headers()  # ПОЯСНЕНИЕ: обновляется значение переменной headers.
            data = self._build_request_data(self.conversation_history)  # ПОЯСНЕНИЕ: обновляется значение переменной data.

            # Make request
            response = self._make_request("POST", self._get_chat_endpoint(), headers, data)  # ПОЯСНЕНИЕ: обновляется значение переменной response.

            # Parse response
            assistant_response = self._parse_response(response)  # ПОЯСНЕНИЕ: обновляется значение переменной assistant_response.
            elapsed = time.time() - start_time  # ПОЯСНЕНИЕ: обновляется значение переменной elapsed.

            # Add to history
            self.add_to_history("assistant", assistant_response)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

            return assistant_response, elapsed  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except APIError as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            elapsed = time.time() - start_time  # ПОЯСНЕНИЕ: обновляется значение переменной elapsed.
            # Remove the user message we added since the request failed
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                self.conversation_history.pop()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return f"Error: {e.message}", elapsed  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            elapsed = time.time() - start_time  # ПОЯСНЕНИЕ: обновляется значение переменной elapsed.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                self.conversation_history.pop()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            logger.exception(f"[{self.name}] Unexpected error")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return f"Error: {str(e)}", elapsed  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_get_chat_endpoint` — выполняет отдельный шаг бизнес-логики.
    def _get_chat_endpoint(self) -> str:  # ПОЯСНЕНИЕ: объявляется функция _get_chat_endpoint с параметрами из сигнатуры.
        """Get the chat completion endpoint - override if needed"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return "/chat/completions"  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `test_connection` — выполняет отдельный шаг бизнес-логики.
    def test_connection(self) -> bool:  # ПОЯСНЕНИЕ: объявляется функция test_connection с параметрами из сигнатуры.
        """Test connection to the API"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not self.api_key:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.is_connected = False  # ПОЯСНЕНИЕ: обновляется значение переменной self.is_connected.
            return False  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            # Simple test request
            headers = self._get_headers()  # ПОЯСНЕНИЕ: обновляется значение переменной headers.
            data = self._build_request_data([{"role": "user", "content": "Hi"}])  # ПОЯСНЕНИЕ: обновляется значение переменной data.
            data["max_tokens"] = 5  # Minimal response  # ПОЯСНЕНИЕ: обновляется значение переменной data["max_tokens"].

            self._make_request("POST", self._get_chat_endpoint(), headers, data, timeout=15)  # ПОЯСНЕНИЕ: обновляется значение переменной self._make_request("POST", self._get_chat_endpoint.
            self.is_connected = True  # ПОЯСНЕНИЕ: обновляется значение переменной self.is_connected.
            return True  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            logger.warning(f"[{self.name}] Connection test failed: {e}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            self.is_connected = False  # ПОЯСНЕНИЕ: обновляется значение переменной self.is_connected.
            return False  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
