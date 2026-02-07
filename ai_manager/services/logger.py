# НАЗНАЧЕНИЕ ФАЙЛА: Сервис журналирования: логи запросов/ошибок и вычисление метрик.
"""
Application Logger with metrics tracking
"""

import os  # ПОЯСНЕНИЕ: импортируется модуль os.
import json  # ПОЯСНЕНИЕ: импортируется модуль json.
import logging  # ПОЯСНЕНИЕ: импортируется модуль logging.
from datetime import datetime  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from typing import Dict, List, Optional  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from collections import deque  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from dataclasses import dataclass, asdict  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from statistics import mean, median  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.


@dataclass  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
# ЛОГИЧЕСКИЙ БЛОК: класс `ResponseLogEntry` — объединяет состояние и поведение подсистемы.
class ResponseLogEntry:  # ПОЯСНЕНИЕ: объявляется класс ResponseLogEntry.
    """Log entry for API response"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
    timestamp: str  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    provider: str  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    question: str  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    response: str  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    elapsed_time: float  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    success: bool  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    tokens_used: int = 0  # ПОЯСНЕНИЕ: обновляется значение переменной tokens_used: int.
    model: str = ""  # ПОЯСНЕНИЕ: обновляется значение переменной model: str.


@dataclass  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
# ЛОГИЧЕСКИЙ БЛОК: класс `ErrorLogEntry` — объединяет состояние и поведение подсистемы.
class ErrorLogEntry:  # ПОЯСНЕНИЕ: объявляется класс ErrorLogEntry.
    """Log entry for errors"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
    timestamp: str  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    provider: str  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    error: str  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    details: str  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    error_code: int = 0  # ПОЯСНЕНИЕ: обновляется значение переменной error_code: int.
    retryable: bool = False  # ПОЯСНЕНИЕ: обновляется значение переменной retryable: bool.


@dataclass  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
# ЛОГИЧЕСКИЙ БЛОК: класс `ProviderMetrics` — объединяет состояние и поведение подсистемы.
class ProviderMetrics:  # ПОЯСНЕНИЕ: объявляется класс ProviderMetrics.
    """Metrics for a single provider"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
    total_requests: int = 0  # ПОЯСНЕНИЕ: обновляется значение переменной total_requests: int.
    successful_requests: int = 0  # ПОЯСНЕНИЕ: обновляется значение переменной successful_requests: int.
    failed_requests: int = 0  # ПОЯСНЕНИЕ: обновляется значение переменной failed_requests: int.
    total_time: float = 0.0  # ПОЯСНЕНИЕ: обновляется значение переменной total_time: float.
    total_tokens: int = 0  # ПОЯСНЕНИЕ: обновляется значение переменной total_tokens: int.

    @property  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `success_rate` — выполняет отдельный шаг бизнес-логики.
    def success_rate(self) -> float:  # ПОЯСНЕНИЕ: объявляется функция success_rate с параметрами из сигнатуры.
        """Описание: функция `success_rate`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if self.total_requests == 0:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return 0.0  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        return self.successful_requests / self.total_requests * 100  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    @property  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `avg_response_time` — выполняет отдельный шаг бизнес-логики.
    def avg_response_time(self) -> float:  # ПОЯСНЕНИЕ: объявляется функция avg_response_time с параметрами из сигнатуры.
        """Описание: функция `avg_response_time`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if self.successful_requests == 0:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return 0.0  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        return self.total_time / self.successful_requests  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `to_dict` — выполняет отдельный шаг бизнес-логики.
    def to_dict(self) -> dict:  # ПОЯСНЕНИЕ: объявляется функция to_dict с параметрами из сигнатуры.
        """Описание: функция `to_dict`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return {  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
            "total_requests": self.total_requests,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "successful_requests": self.successful_requests,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "failed_requests": self.failed_requests,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "success_rate": round(self.success_rate, 1),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "avg_response_time": round(self.avg_response_time, 2),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "total_tokens": self.total_tokens  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        }  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.


# ЛОГИЧЕСКИЙ БЛОК: класс `AppLogger` — объединяет состояние и поведение подсистемы.
class AppLogger:  # ПОЯСНЕНИЕ: объявляется класс AppLogger.
    """Application logger with response/error tracking and metrics"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.

    # ЛОГИЧЕСКИЙ БЛОК: функция `__init__` — выполняет отдельный шаг бизнес-логики.
    def __init__(self, log_dir: str = "logs", max_responses: int = 1000, max_errors: int = 500):  # ПОЯСНЕНИЕ: объявляется функция __init__ с параметрами из сигнатуры.
        """Описание: функция `__init__`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.log_dir = log_dir  # ПОЯСНЕНИЕ: обновляется значение переменной self.log_dir.
        self.session_start = datetime.now()  # ПОЯСНЕНИЕ: обновляется значение переменной self.session_start.

        # In-memory logs with size limits
        self.responses_log: deque = deque(maxlen=max_responses)  # ПОЯСНЕНИЕ: обновляется значение переменной self.responses_log: deque.
        self.errors_log: deque = deque(maxlen=max_errors)  # ПОЯСНЕНИЕ: обновляется значение переменной self.errors_log: deque.

        # Provider metrics
        self.metrics: Dict[str, ProviderMetrics] = {}  # ПОЯСНЕНИЕ: обновляется значение переменной self.metrics: Dict[str, ProviderMetrics].

        # Recent response times for each provider (for trend analysis)
        self._response_times: Dict[str, deque] = {}  # ПОЯСНЕНИЕ: обновляется значение переменной self._response_times: Dict[str, deque].

        # Create log directory
        os.makedirs(log_dir, exist_ok=True)  # ПОЯСНЕНИЕ: обновляется значение переменной os.makedirs(log_dir, exist_ok.

        # Setup file logging
        self._setup_file_logging()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_setup_file_logging` — выполняет отдельный шаг бизнес-логики.
    def _setup_file_logging(self):  # ПОЯСНЕНИЕ: объявляется функция _setup_file_logging с параметрами из сигнатуры.
        """Setup file-based logging"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        log_file = os.path.join(  # ПОЯСНЕНИЕ: обновляется значение переменной log_file.
            self.log_dir,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            f"app_{self.session_start.strftime('%Y%m%d_%H%M%S')}.log"  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Create a new handler for this session
        file_handler = logging.FileHandler(log_file, encoding='utf-8')  # ПОЯСНЕНИЕ: обновляется значение переменной file_handler.
        file_handler.setLevel(logging.INFO)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        file_handler.setFormatter(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Get root logger and add handler
        root_logger = logging.getLogger()  # ПОЯСНЕНИЕ: обновляется значение переменной root_logger.
        root_logger.setLevel(logging.INFO)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        root_logger.addHandler(file_handler)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Also log to console in debug mode
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            console_handler = logging.StreamHandler()  # ПОЯСНЕНИЕ: обновляется значение переменной console_handler.
            console_handler.setLevel(logging.WARNING)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            root_logger.addHandler(console_handler)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        self.logger = logging.getLogger(__name__)  # ПОЯСНЕНИЕ: обновляется значение переменной self.logger.
        self.logger.info(f"Session started at {self.session_start}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_ensure_metrics` — выполняет отдельный шаг бизнес-логики.
    def _ensure_metrics(self, provider: str):  # ПОЯСНЕНИЕ: объявляется функция _ensure_metrics с параметрами из сигнатуры.
        """Ensure metrics exist for provider"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if provider not in self.metrics:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.metrics[provider] = ProviderMetrics()  # ПОЯСНЕНИЕ: обновляется значение переменной self.metrics[provider].
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if provider not in self._response_times:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self._response_times[provider] = deque(maxlen=100)  # ПОЯСНЕНИЕ: обновляется значение переменной self._response_times[provider].

    # ЛОГИЧЕСКИЙ БЛОК: функция `log_response` — выполняет отдельный шаг бизнес-логики.
    def log_response(  # ПОЯСНЕНИЕ: объявляется функция log_response с параметрами из сигнатуры.
        self,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        provider: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        question: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        response: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        elapsed: float,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        success: bool = True,  # ПОЯСНЕНИЕ: обновляется значение переменной success: bool.
        tokens_used: int = 0,  # ПОЯСНЕНИЕ: обновляется значение переменной tokens_used: int.
        model: str = ""  # ПОЯСНЕНИЕ: обновляется значение переменной model: str.
    ):  # ПОЯСНЕНИЕ: начинается новый логический блок кода.
        """Log AI response and update metrics"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self._ensure_metrics(provider)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        entry = ResponseLogEntry(  # ПОЯСНЕНИЕ: обновляется значение переменной entry.
            timestamp=datetime.now().isoformat(),  # ПОЯСНЕНИЕ: обновляется значение переменной timestamp.
            provider=provider,  # ПОЯСНЕНИЕ: обновляется значение переменной provider.
            question=question[:500],  # Truncate for log  # ПОЯСНЕНИЕ: обновляется значение переменной question.
            response=response[:5000] if success else response,  # Limit response size  # ПОЯСНЕНИЕ: обновляется значение переменной response.
            elapsed_time=elapsed,  # ПОЯСНЕНИЕ: обновляется значение переменной elapsed_time.
            success=success,  # ПОЯСНЕНИЕ: обновляется значение переменной success.
            tokens_used=tokens_used,  # ПОЯСНЕНИЕ: обновляется значение переменной tokens_used.
            model=model  # ПОЯСНЕНИЕ: обновляется значение переменной model.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.responses_log.append(asdict(entry))  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Update metrics
        metrics = self.metrics[provider]  # ПОЯСНЕНИЕ: обновляется значение переменной metrics.
        metrics.total_requests += 1  # ПОЯСНЕНИЕ: обновляется значение переменной metrics.total_requests +.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if success:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            metrics.successful_requests += 1  # ПОЯСНЕНИЕ: обновляется значение переменной metrics.successful_requests +.
            metrics.total_time += elapsed  # ПОЯСНЕНИЕ: обновляется значение переменной metrics.total_time +.
            metrics.total_tokens += tokens_used  # ПОЯСНЕНИЕ: обновляется значение переменной metrics.total_tokens +.
            self._response_times[provider].append(elapsed)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        else:  # ПОЯСНЕНИЕ: выполняется альтернативная ветка else.
            metrics.failed_requests += 1  # ПОЯСНЕНИЕ: обновляется значение переменной metrics.failed_requests +.

        # Log to file
        status = "SUCCESS" if success else "FAILED"  # ПОЯСНЕНИЕ: обновляется значение переменной status.
        self.logger.info(f"[{provider}] {status} | {elapsed:.2f}s | Q: {question[:100]}...")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `log_error` — выполняет отдельный шаг бизнес-логики.
    def log_error(  # ПОЯСНЕНИЕ: объявляется функция log_error с параметрами из сигнатуры.
        self,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        provider: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        error: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        details: str = "",  # ПОЯСНЕНИЕ: обновляется значение переменной details: str.
        error_code: int = 0,  # ПОЯСНЕНИЕ: обновляется значение переменной error_code: int.
        retryable: bool = False  # ПОЯСНЕНИЕ: обновляется значение переменной retryable: bool.
    ):  # ПОЯСНЕНИЕ: начинается новый логический блок кода.
        """Log error with details"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        entry = ErrorLogEntry(  # ПОЯСНЕНИЕ: обновляется значение переменной entry.
            timestamp=datetime.now().isoformat(),  # ПОЯСНЕНИЕ: обновляется значение переменной timestamp.
            provider=provider,  # ПОЯСНЕНИЕ: обновляется значение переменной provider.
            error=error,  # ПОЯСНЕНИЕ: обновляется значение переменной error.
            details=details[:1000],  # ПОЯСНЕНИЕ: обновляется значение переменной details.
            error_code=error_code,  # ПОЯСНЕНИЕ: обновляется значение переменной error_code.
            retryable=retryable  # ПОЯСНЕНИЕ: обновляется значение переменной retryable.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.errors_log.append(asdict(entry))  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        self.logger.error(f"[{provider}] {error} | Code: {error_code} | {details[:200]}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get_responses_log` — выполняет отдельный шаг бизнес-логики.
    def get_responses_log(self) -> List[dict]:  # ПОЯСНЕНИЕ: объявляется функция get_responses_log с параметрами из сигнатуры.
        """Get responses log"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return list(self.responses_log)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get_errors_log` — выполняет отдельный шаг бизнес-логики.
    def get_errors_log(self) -> List[dict]:  # ПОЯСНЕНИЕ: объявляется функция get_errors_log с параметрами из сигнатуры.
        """Get errors log"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return list(self.errors_log)  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get_provider_metrics` — выполняет отдельный шаг бизнес-логики.
    def get_provider_metrics(self, provider: str) -> Optional[dict]:  # ПОЯСНЕНИЕ: объявляется функция get_provider_metrics с параметрами из сигнатуры.
        """Get metrics for a specific provider"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if provider in self.metrics:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return self.metrics[provider].to_dict()  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get_all_metrics` — выполняет отдельный шаг бизнес-логики.
    def get_all_metrics(self) -> Dict[str, dict]:  # ПОЯСНЕНИЕ: объявляется функция get_all_metrics с параметрами из сигнатуры.
        """Get metrics for all providers"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return {name: m.to_dict() for name, m in self.metrics.items()}  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get_response_time_trend` — выполняет отдельный шаг бизнес-логики.
    def get_response_time_trend(self, provider: str) -> List[float]:  # ПОЯСНЕНИЕ: объявляется функция get_response_time_trend с параметрами из сигнатуры.
        """Get recent response times for trend analysis"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if provider in self._response_times:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return list(self._response_times[provider])  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        return []  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `export_logs` — выполняет отдельный шаг бизнес-логики.
    def export_logs(self, filepath: str, log_type: str = "all") -> bool:  # ПОЯСНЕНИЕ: объявляется функция export_logs с параметрами из сигнатуры.
        """Export logs to file"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            with open(filepath, 'w', encoding='utf-8') as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                f.write("=" * 70 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".
                f.write(f"AI Manager Log Export\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write(f"Session: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write(f"Export: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write("=" * 70 + "\n\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".

                # Metrics summary
                f.write("PROVIDER METRICS\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write("-" * 50 + "\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
                for name, metrics in self.metrics.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                    m = metrics.to_dict()  # ПОЯСНЕНИЕ: обновляется значение переменной m.
                    f.write(f"\n{name}:\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    f.write(f"  Requests: {m['total_requests']} (Success: {m['success_rate']:.1f}%)\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    f.write(f"  Avg Time: {m['avg_response_time']:.2f}s\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    f.write(f"  Tokens: {m['total_tokens']}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write("\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if log_type in ["all", "responses"]:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    f.write("=" * 70 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".
                    f.write("RESPONSES LOG\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    f.write("=" * 70 + "\n\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".
                    # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
                    for entry in self.responses_log:  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                        f.write(f"[{entry['timestamp'][:19]}] {entry['provider']}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        f.write(f"Model: {entry.get('model', 'N/A')}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        f.write(f"Q: {entry['question']}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        status = "OK" if entry['success'] else "FAIL"  # ПОЯСНЕНИЕ: обновляется значение переменной status.
                        f.write(f"Status: {status} | Time: {entry['elapsed_time']:.2f}s\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        f.write(f"Response: {entry['response'][:500]}...\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        f.write("-" * 50 + "\n\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if log_type in ["all", "errors"]:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    f.write("\n" + "=" * 70 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write("\n" + ".
                    f.write("ERRORS LOG\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    f.write("=" * 70 + "\n\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".
                    # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
                    for entry in self.errors_log:  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                        f.write(f"[{entry['timestamp'][:19]}] {entry['provider']}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        f.write(f"Error: {entry['error']}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        f.write(f"Code: {entry.get('error_code', 'N/A')}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                        if entry['details']:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                            f.write(f"Details: {entry['details']}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        f.write("-" * 50 + "\n\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

                f.write("\n" + "=" * 70 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write("\n" + ".
                f.write(f"Total responses: {len(self.responses_log)}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write(f"Total errors: {len(self.errors_log)}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write("=" * 70 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".

            return True  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            self.logger.error(f"Failed to export logs: {e}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return False  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `clear_logs` — выполняет отдельный шаг бизнес-логики.
    def clear_logs(self):  # ПОЯСНЕНИЕ: объявляется функция clear_logs с параметрами из сигнатуры.
        """Clear in-memory logs"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.responses_log.clear()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.errors_log.clear()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `reset_metrics` — выполняет отдельный шаг бизнес-логики.
    def reset_metrics(self):  # ПОЯСНЕНИЕ: объявляется функция reset_metrics с параметрами из сигнатуры.
        """Reset all metrics"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.metrics.clear()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self._response_times.clear()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.


# Singleton instance
_logger_instance: Optional[AppLogger] = None  # ПОЯСНЕНИЕ: обновляется значение переменной _logger_instance: Optional[AppLogger].


# ЛОГИЧЕСКИЙ БЛОК: функция `get_logger` — выполняет отдельный шаг бизнес-логики.
def get_logger(log_dir: str = "logs") -> AppLogger:  # ПОЯСНЕНИЕ: объявляется функция get_logger с параметрами из сигнатуры.
    """Get or create logger instance"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
    global _logger_instance  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
    if _logger_instance is None:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
        _logger_instance = AppLogger(log_dir)  # ПОЯСНЕНИЕ: обновляется значение переменной _logger_instance.
    return _logger_instance  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
