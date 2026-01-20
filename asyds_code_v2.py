"""
Telegram бот для трех нейросетей: GigaChat, Groq, Mistral
ВЕРСИЯ v3.3 - Enterprise + Scalability

=== ROADMAP ===
v3.1 - Надёжность:
  - Circuit Breaker per AI provider
  - Graceful shutdown с drain
  - TTL + eviction для всех компонентов
  - Input validation & sanitization
  - Safe retry logic

v3.2 - Наблюдаемость:
  - Prometheus metrics (/metrics endpoint)
  - Latency histograms per provider
  - Error rate counters
  - /health, /ready, /status endpoints
  - Request correlation (contextvars)

v3.3 - Масштабирование:
  - Dynamic worker pool (scale up/down)
  - Redis cache adapter (optional)
  - K8s ready (probes, stateless option)
  - HPA compatible metrics

=== STATELESS MODE (for K8s) ===
Для горизонтального масштабирования:
1. REDIS_ENABLED=true - кэш в Redis (shared между pods)
2. Branches хранятся в памяти (sticky sessions) или JSON файле
3. Queue в памяти (для decoupling используйте RabbitMQ/Redis Streams)

=== KUBERNETES ===
- Liveness: GET /health:8080
- Readiness: GET /ready:8080
- Metrics: GET /metrics:8080 (Prometheus)

=== КОНФИГУРАЦИЯ ===
Все настройки через .env или переменные окружения.
См. класс Config для полного списка параметров.
"""

import asyncio
import logging
import logging.handlers
import aiohttp
import aiohttp.web
import ssl
import time
import uuid
import io
import hashlib
import os
import queue
import re
import contextvars
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from collections import deque
from functools import wraps
from enum import Enum

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# ============ [10] КОНФИГУРАЦИЯ С PYDANTIC-SETTINGS ============
try:
    from pydantic_settings import BaseSettings
    from pydantic import field_validator, Field

    class Config(BaseSettings):
        """Конфигурация с валидацией и загрузкой из .env"""

        # API ключи (загружаются из .env)
        BOT_TOKEN: str = Field(default="")
        SBER_API_KEY: str = Field(default="")
        GROQ_API_KEY: str = Field(default="")
        MISTRAL_API_KEY: str = Field(default="")

        # Настройки производительности
        MAX_CONCURRENT_API_CALLS: int = 15
        RATE_LIMIT_PER_USER: int = 5
        RATE_LIMIT_PERIOD: int = 60
        USER_TTL_SECONDS: int = 3600  # TTL для очистки неактивных пользователей

        # [7] Дифференцированные таймауты
        TIMEOUT_OAUTH: int = 10      # OAuth быстрая операция
        TIMEOUT_CHAT: int = 45       # Обычный чат
        TIMEOUT_VISION: int = 90     # Обработка изображений
        TIMEOUT_FILE: int = 60       # Обработка файлов

        # Настройки очереди
        QUEUE_MAX_SIZE: int = 1000
        MIN_WORKERS: int = 2
        MAX_WORKERS: int = 20

        # Priority Queue (v3.4)
        PRIORITY_ENABLED: bool = True
        PREMIUM_USER_IDS: str = ""  # Comma-separated list of premium user IDs

        # Ограничения входных данных (v3.1)
        MAX_QUESTION_LENGTH: int = 10000    # Максимальная длина вопроса
        MAX_FILE_SIZE_KB: int = 500         # Максимальный размер файла в KB
        MAX_CONTEXT_MESSAGES: int = 20      # Максимум сообщений в контексте
        MIN_QUESTION_LENGTH: int = 2        # Минимальная длина вопроса

        # SSL настройки
        DISABLE_SSL_VERIFY: bool = False  # Только для разработки!

        # Webhook
        USE_WEBHOOK: bool = False
        WEBHOOK_URL: str = "https://your-domain.com/webhook"
        WEBHOOK_PATH: str = "/webhook"
        WEBHOOK_SECRET: str = "your-secret-token"

        # Redis (optional, for scaling)
        REDIS_ENABLED: bool = False
        REDIS_URL: str = "redis://localhost:6379/0"
        REDIS_CACHE_TTL: int = 3600  # TTL для кэша в Redis
        REDIS_BRANCHES_TTL: int = 86400  # TTL для веток в Redis (24h)

        # Observability
        OBSERVABILITY_PORT: int = 8080

        @field_validator('BOT_TOKEN')
        @classmethod
        def validate_bot_token(cls, v: str) -> str:
            if v and not re.match(r'^\d+:[A-Za-z0-9_-]+$', v):
                raise ValueError('Invalid bot token format')
            return v

        @field_validator('SBER_API_KEY', 'GROQ_API_KEY', 'MISTRAL_API_KEY')
        @classmethod
        def validate_api_key(cls, v: str) -> str:
            # Маскируем ключи при логировании
            return v

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"

    config = Config()

except ImportError:
    # Fallback если pydantic-settings не установлен
    from dataclasses import dataclass

    @dataclass
    class Config:
        BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
        SBER_API_KEY: str = os.getenv("SBER_API_KEY", "")
        GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
        MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")

        MAX_CONCURRENT_API_CALLS: int = 15
        RATE_LIMIT_PER_USER: int = 5
        RATE_LIMIT_PERIOD: int = 60
        USER_TTL_SECONDS: int = 3600

        TIMEOUT_OAUTH: int = 10
        TIMEOUT_CHAT: int = 45
        TIMEOUT_VISION: int = 90
        TIMEOUT_FILE: int = 60

        QUEUE_MAX_SIZE: int = 1000
        MIN_WORKERS: int = 2
        MAX_WORKERS: int = 20

        DISABLE_SSL_VERIFY: bool = os.getenv("DISABLE_SSL_VERIFY", "").lower() == "true"

        USE_WEBHOOK: bool = False
        WEBHOOK_URL: str = "https://your-domain.com/webhook"
        WEBHOOK_PATH: str = "/webhook"
        WEBHOOK_SECRET: str = "your-secret-token"

    config = Config()


# ============ [9] АСИНХРОННОЕ ЛОГИРОВАНИЕ ============
class AsyncQueueHandler(logging.handlers.QueueHandler):
    """Неблокирующий handler для логирования"""
    pass


class SecretMaskingFilter(logging.Filter):
    """Фильтр для маскирования секретов в логах"""

    PATTERNS = [
        (re.compile(r'Bearer [A-Za-z0-9_\-\.]+'), 'Bearer ***MASKED***'),
        (re.compile(r'token["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]+'), 'token: ***MASKED***'),
        (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]+', re.I), 'api_key: ***MASKED***'),
        (re.compile(r'\d{10}:[A-Za-z0-9_-]{35}'), '***BOT_TOKEN_MASKED***'),  # Telegram bot token
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


class TextLimitFilter(logging.Filter):
    """Ограничение длины логируемого текста (защита от PII)"""
    MAX_LENGTH = 500

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'msg') and isinstance(record.msg, str) and len(record.msg) > self.MAX_LENGTH:
            record.msg = record.msg[:self.MAX_LENGTH] + '... [TRUNCATED]'
        return True


def setup_async_logging() -> logging.Logger:
    """Настройка асинхронного логирования"""

    # Создаем очередь для логов
    log_queue: queue.Queue = queue.Queue(-1)

    # File handler (будет работать в отдельном потоке)
    file_handler = logging.FileHandler(
        "multi_ai_bot_v2.log",
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s',
        defaults={'request_id': 'N/A'}
    ))

    # Stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))

    # Queue listener (обрабатывает логи асинхронно)
    listener = logging.handlers.QueueListener(
        log_queue,
        file_handler,
        stream_handler,
        respect_handler_level=True
    )
    listener.start()

    # Queue handler (неблокирующий)
    queue_handler = AsyncQueueHandler(log_queue)

    # Настраиваем root logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(queue_handler)

    # Добавляем фильтры безопасности
    logger.addFilter(SecretMaskingFilter())
    logger.addFilter(TextLimitFilter())

    return logger


logger = setup_async_logging()


# ============ [11] МЕТРИКИ И ЛОГИРОВАНИЕ СБОЕВ ============
class MetricsCollector:
    """Сборщик метрик для мониторинга"""

    def __init__(self):
        self.requests_total = 0
        self.requests_success = 0
        self.requests_failed = 0
        self.requests_timeout = 0
        self.requests_rate_limited = 0
        self.queue_overflows = 0
        self.retries_total = 0
        self.errors_by_service: Dict[str, int] = {"GigaChat": 0, "Groq": 0, "Mistral": 0}
        self.response_times: Dict[str, List[float]] = {"GigaChat": [], "Groq": [], "Mistral": []}
        self._lock = asyncio.Lock()

    async def record_request(self, service: str, success: bool, response_time: float,
                            error_type: Optional[str] = None):
        async with self._lock:
            self.requests_total += 1

            if success:
                self.requests_success += 1
            else:
                self.requests_failed += 1
                self.errors_by_service[service] = self.errors_by_service.get(service, 0) + 1

                if error_type == "Timeout":
                    self.requests_timeout += 1
                elif error_type == "Rate limit exceeded":
                    self.requests_rate_limited += 1

            # Храним последние 100 времён ответа для статистики
            if service in self.response_times:
                self.response_times[service].append(response_time)
                if len(self.response_times[service]) > 100:
                    self.response_times[service].pop(0)

        # Отправляем в Prometheus metrics (если инициализирован)
        if 'prom_metrics' in globals():
            await prom_metrics.record_request(service, success, response_time, error_type)

    async def record_retry(self):
        async with self._lock:
            self.retries_total += 1

    async def record_queue_overflow(self):
        async with self._lock:
            self.queue_overflows += 1
            logger.warning(
                f"QUEUE_OVERFLOW: total_overflows={self.queue_overflows}",
                extra={'request_id': 'SYSTEM'}
            )

    def get_avg_response_time(self, service: str) -> float:
        times = self.response_times.get(service, [])
        return sum(times) / len(times) if times else 0.0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "requests_total": self.requests_total,
            "requests_success": self.requests_success,
            "requests_failed": self.requests_failed,
            "requests_timeout": self.requests_timeout,
            "requests_rate_limited": self.requests_rate_limited,
            "queue_overflows": self.queue_overflows,
            "retries_total": self.retries_total,
            "errors_by_service": self.errors_by_service,
            "avg_response_times": {
                service: self.get_avg_response_time(service)
                for service in self.response_times
            },
            "success_rate": (
                self.requests_success / self.requests_total * 100
                if self.requests_total > 0 else 0
            )
        }


metrics = MetricsCollector()


# ============ PROMETHEUS METRICS ============
class PrometheusMetrics:
    """
    Prometheus-совместимый сборщик метрик.
    Экспортирует метрики в формате Prometheus text exposition.
    """

    # Bucket границы для гистограмм latency (в секундах)
    LATENCY_BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float('inf'))

    def __init__(self):
        self._lock = asyncio.Lock()

        # Counters
        self._requests_total: Dict[str, int] = {}  # {service: count}
        self._requests_success: Dict[str, int] = {}
        self._requests_failed: Dict[str, int] = {}
        self._errors_by_type: Dict[str, Dict[str, int]] = {}  # {service: {error_type: count}}

        # Histograms (latency)
        self._latency_buckets: Dict[str, Dict[float, int]] = {}  # {service: {bucket: count}}
        self._latency_sum: Dict[str, float] = {}
        self._latency_count: Dict[str, int] = {}

        # Gauges
        self._queue_size = 0
        self._active_workers = 0
        self._active_requests = 0

        # Circuit breaker states
        self._circuit_states: Dict[str, str] = {}

        # Initialize for all services
        for service in ["GigaChat", "Groq", "Mistral"]:
            self._init_service(service)

    def _init_service(self, service: str):
        """Инициализация метрик для сервиса"""
        self._requests_total[service] = 0
        self._requests_success[service] = 0
        self._requests_failed[service] = 0
        self._errors_by_type[service] = {}
        self._latency_sum[service] = 0.0
        self._latency_count[service] = 0
        self._latency_buckets[service] = {b: 0 for b in self.LATENCY_BUCKETS}

    async def record_request(
        self,
        service: str,
        success: bool,
        latency: float,
        error_type: Optional[str] = None
    ):
        """Записать метрики запроса"""
        async with self._lock:
            self._requests_total[service] = self._requests_total.get(service, 0) + 1

            if success:
                self._requests_success[service] = self._requests_success.get(service, 0) + 1
            else:
                self._requests_failed[service] = self._requests_failed.get(service, 0) + 1
                if error_type:
                    if service not in self._errors_by_type:
                        self._errors_by_type[service] = {}
                    self._errors_by_type[service][error_type] = \
                        self._errors_by_type[service].get(error_type, 0) + 1

            # Обновляем гистограмму latency
            self._latency_sum[service] = self._latency_sum.get(service, 0.0) + latency
            self._latency_count[service] = self._latency_count.get(service, 0) + 1

            if service not in self._latency_buckets:
                self._latency_buckets[service] = {b: 0 for b in self.LATENCY_BUCKETS}

            for bucket in self.LATENCY_BUCKETS:
                if latency <= bucket:
                    self._latency_buckets[service][bucket] += 1

    def set_queue_size(self, size: int):
        """Установить размер очереди"""
        self._queue_size = size

    def set_active_workers(self, count: int):
        """Установить количество активных воркеров"""
        self._active_workers = count

    def set_active_requests(self, count: int):
        """Установить количество активных запросов"""
        self._active_requests = count

    def set_circuit_state(self, service: str, state: str):
        """Установить состояние circuit breaker"""
        self._circuit_states[service] = state

    def export(self) -> str:
        """Экспорт метрик в формате Prometheus text exposition"""
        lines = []

        # HELP и TYPE для каждой метрики
        lines.append("# HELP bot_requests_total Total number of requests by service")
        lines.append("# TYPE bot_requests_total counter")
        for service, count in self._requests_total.items():
            lines.append(f'bot_requests_total{{service="{service}"}} {count}')

        lines.append("")
        lines.append("# HELP bot_requests_success_total Successful requests by service")
        lines.append("# TYPE bot_requests_success_total counter")
        for service, count in self._requests_success.items():
            lines.append(f'bot_requests_success_total{{service="{service}"}} {count}')

        lines.append("")
        lines.append("# HELP bot_requests_failed_total Failed requests by service")
        lines.append("# TYPE bot_requests_failed_total counter")
        for service, count in self._requests_failed.items():
            lines.append(f'bot_requests_failed_total{{service="{service}"}} {count}')

        lines.append("")
        lines.append("# HELP bot_errors_total Errors by service and type")
        lines.append("# TYPE bot_errors_total counter")
        for service, errors in self._errors_by_type.items():
            for error_type, count in errors.items():
                lines.append(f'bot_errors_total{{service="{service}",error_type="{error_type}"}} {count}')

        # Latency histogram
        lines.append("")
        lines.append("# HELP bot_request_latency_seconds Request latency histogram")
        lines.append("# TYPE bot_request_latency_seconds histogram")
        for service in self._latency_buckets:
            for bucket, count in self._latency_buckets[service].items():
                le = "+Inf" if bucket == float('inf') else str(bucket)
                lines.append(f'bot_request_latency_seconds_bucket{{service="{service}",le="{le}"}} {count}')
            lines.append(f'bot_request_latency_seconds_sum{{service="{service}"}} {self._latency_sum.get(service, 0):.3f}')
            lines.append(f'bot_request_latency_seconds_count{{service="{service}"}} {self._latency_count.get(service, 0)}')

        # Gauges
        lines.append("")
        lines.append("# HELP bot_queue_size Current queue size")
        lines.append("# TYPE bot_queue_size gauge")
        lines.append(f"bot_queue_size {self._queue_size}")

        lines.append("")
        lines.append("# HELP bot_active_workers Number of active workers")
        lines.append("# TYPE bot_active_workers gauge")
        lines.append(f"bot_active_workers {self._active_workers}")

        lines.append("")
        lines.append("# HELP bot_active_requests Number of active requests")
        lines.append("# TYPE bot_active_requests gauge")
        lines.append(f"bot_active_requests {self._active_requests}")

        # Circuit breaker states (as gauge: 0=closed, 1=half_open, 2=open)
        lines.append("")
        lines.append("# HELP bot_circuit_state Circuit breaker state (0=closed, 1=half_open, 2=open)")
        lines.append("# TYPE bot_circuit_state gauge")
        state_map = {"closed": 0, "half_open": 1, "open": 2}
        for service, state in self._circuit_states.items():
            state_value = state_map.get(state, -1)
            lines.append(f'bot_circuit_state{{service="{service}"}} {state_value}')

        # Error rate (calculated)
        lines.append("")
        lines.append("# HELP bot_error_rate Error rate per service (0-1)")
        lines.append("# TYPE bot_error_rate gauge")
        for service in self._requests_total:
            total = self._requests_total.get(service, 0)
            failed = self._requests_failed.get(service, 0)
            rate = failed / total if total > 0 else 0.0
            lines.append(f'bot_error_rate{{service="{service}"}} {rate:.4f}')

        return "\n".join(lines) + "\n"


# Глобальный Prometheus collector
prom_metrics = PrometheusMetrics()


# ============ REQUEST CORRELATION (contextvars) ============
# Context variable для request_id - доступен во всех корутинах
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='N/A')


def get_request_id() -> str:
    """Получить текущий request_id из контекста"""
    return request_id_var.get()


def set_request_id(request_id: str) -> contextvars.Token:
    """Установить request_id в контекст"""
    return request_id_var.set(request_id)


# ============ OBSERVABILITY HTTP SERVER ============
class ObservabilityServer:
    """
    HTTP сервер для observability endpoints:
    - /metrics - Prometheus metrics
    - /health - Liveness probe
    - /ready - Readiness probe
    - /status - Detailed status (JSON)
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app: Optional[aiohttp.web.Application] = None
        self.runner: Optional[aiohttp.web.AppRunner] = None
        self.site: Optional[aiohttp.web.TCPSite] = None

    async def metrics_handler(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Handler для /metrics endpoint"""
        # Обновляем gauge метрики перед экспортом
        prom_metrics.set_queue_size(request_queue.queue.qsize() if 'request_queue' in globals() else 0)
        prom_metrics.set_active_workers(len([w for w in request_queue.workers if not w.done()]) if 'request_queue' in globals() else 0)
        prom_metrics.set_active_requests(shutdown_manager._active_requests if 'shutdown_manager' in globals() else 0)

        # Обновляем circuit breaker states
        if 'gigachat_circuit' in globals():
            prom_metrics.set_circuit_state("GigaChat", gigachat_circuit.state.value)
            prom_metrics.set_circuit_state("Groq", groq_circuit.state.value)
            prom_metrics.set_circuit_state("Mistral", mistral_circuit.state.value)

        body = prom_metrics.export()
        return aiohttp.web.Response(
            text=body,
            content_type="text/plain; charset=utf-8"
        )

    async def health_handler(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Handler для /health (liveness probe)"""
        # Liveness: если код выполняется, бот жив
        return aiohttp.web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        })

    async def ready_handler(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Handler для /ready (readiness probe)"""
        is_ready = shutdown_manager.is_ready if 'shutdown_manager' in globals() else False

        if is_ready:
            return aiohttp.web.json_response({
                "status": "ready",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return aiohttp.web.json_response(
                {"status": "not_ready", "timestamp": datetime.now().isoformat()},
                status=503
            )

    async def status_handler(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Handler для /status (detailed JSON status)"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "version": "3.2",
            "shutdown": shutdown_manager.get_status() if 'shutdown_manager' in globals() else {},
            "metrics": metrics.get_stats() if 'metrics' in globals() else {},
            "queue": request_queue.get_stats() if 'request_queue' in globals() else {},
            "branches": branch_manager.get_stats() if 'branch_manager' in globals() else {},
            "cache": response_cache.get_stats() if 'response_cache' in globals() else {},
            "circuits": {
                "gigachat": gigachat_circuit.get_status() if 'gigachat_circuit' in globals() else {},
                "groq": groq_circuit.get_status() if 'groq_circuit' in globals() else {},
                "mistral": mistral_circuit.get_status() if 'mistral_circuit' in globals() else {},
            }
        }
        return aiohttp.web.json_response(status)

    async def start(self):
        """Запуск HTTP сервера"""
        self.app = aiohttp.web.Application()
        self.app.router.add_get("/metrics", self.metrics_handler)
        self.app.router.add_get("/health", self.health_handler)
        self.app.router.add_get("/ready", self.ready_handler)
        self.app.router.add_get("/status", self.status_handler)

        self.runner = aiohttp.web.AppRunner(self.app)
        await self.runner.setup()

        self.site = aiohttp.web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        logger.info(
            f"Observability server started on http://{self.host}:{self.port}",
            extra={'request_id': 'STARTUP'}
        )
        logger.info(
            f"  - /metrics (Prometheus)\n  - /health (liveness)\n  - /ready (readiness)\n  - /status (JSON)",
            extra={'request_id': 'STARTUP'}
        )

    async def stop(self):
        """Остановка HTTP сервера"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Observability server stopped", extra={'request_id': 'SHUTDOWN'})


# Глобальный observability сервер
observability_server = ObservabilityServer(port=8080)


# ============ [12] СИСТЕМА ВЕТОК ДИАЛОГА ============
class ConversationBranch:
    """Ветка диалога с историей сообщений"""

    def __init__(self, branch_id: str, name: str = ""):
        self.id = branch_id
        self.name = name or f"Ветка {branch_id[:6]}"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.messages: List[Dict[str, str]] = []  # [{"role": "user/assistant", "content": "..."}]
        self.is_active = True

    def add_message(self, role: str, content: str):
        """Добавить сообщение в историю"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()

        # Ограничиваем историю (последние 20 сообщений)
        if len(self.messages) > 20:
            self.messages = self.messages[-20:]

    def get_context(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Получить контекст для API (последние N сообщений)"""
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self.messages[-max_messages:]
        ]

    def clear(self):
        """Очистить историю ветки"""
        self.messages = []
        self.updated_at = datetime.now()

    def to_dict(self, include_messages: bool = True) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": len(self.messages),
            "is_active": self.is_active
        }
        if include_messages:
            result["messages"] = self.messages
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationBranch':
        """Создать ветку из словаря (для загрузки из файла)"""
        branch = cls(data["id"], data.get("name", ""))
        branch.created_at = datetime.fromisoformat(data["created_at"])
        branch.updated_at = datetime.fromisoformat(data["updated_at"])
        branch.messages = data.get("messages", [])
        branch.is_active = data.get("is_active", True)
        return branch


class BranchManager:
    """Менеджер веток диалога для всех пользователей с TTL и persistence"""

    MAX_BRANCHES_PER_USER = 10
    USER_TTL_SECONDS = 86400  # 24 часа неактивности
    CLEANUP_INTERVAL = 600   # 10 минут
    STORAGE_FILE = "branches_data.json"

    def __init__(self):
        # user_id -> {branch_id -> ConversationBranch}
        self.user_branches: Dict[int, Dict[str, ConversationBranch]] = {}
        # user_id -> current_branch_id
        self.current_branch: Dict[int, str] = {}
        # user_id -> last_activity timestamp (для TTL)
        self.user_last_activity: Dict[int, float] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self):
        """Запуск фоновой задачи очистки"""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("BranchManager cleanup task started", extra={'request_id': 'STARTUP'})

    async def stop_cleanup_task(self):
        """Остановка задачи очистки"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _periodic_cleanup(self):
        """Периодическая очистка неактивных пользователей"""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
                await self._cleanup_inactive_users()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"BranchManager cleanup error: {e}", extra={'request_id': 'CLEANUP'})

    async def _cleanup_inactive_users(self):
        """Очистка пользователей без активности > TTL"""
        async with self._lock:
            now = time.time()
            inactive_users = [
                user_id for user_id, last_activity in self.user_last_activity.items()
                if now - last_activity > self.USER_TTL_SECONDS
            ]

            for user_id in inactive_users:
                if user_id in self.user_branches:
                    del self.user_branches[user_id]
                if user_id in self.current_branch:
                    del self.current_branch[user_id]
                if user_id in self.user_last_activity:
                    del self.user_last_activity[user_id]

            if inactive_users:
                logger.info(
                    f"BRANCHES_CLEANUP: Removed {len(inactive_users)} inactive users. "
                    f"Active users: {len(self.user_branches)}",
                    extra={'request_id': 'CLEANUP'}
                )

    def _update_activity(self, user_id: int):
        """Обновить время активности пользователя (вызывается под lock)"""
        self.user_last_activity[user_id] = time.time()

    async def save_to_file(self):
        """Сохранить ветки в JSON файл"""
        async with self._lock:
            try:
                data = {
                    "saved_at": time.time(),
                    "users": {}
                }
                for user_id, branches in self.user_branches.items():
                    data["users"][str(user_id)] = {
                        "current_branch": self.current_branch.get(user_id),
                        "last_activity": self.user_last_activity.get(user_id, time.time()),
                        "branches": {
                            bid: branch.to_dict() for bid, branch in branches.items()
                        }
                    }

                import json
                with open(self.STORAGE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                logger.info(
                    f"BRANCHES_SAVED: {len(self.user_branches)} users saved to {self.STORAGE_FILE}",
                    extra={'request_id': 'PERSISTENCE'}
                )
            except Exception as e:
                logger.error(f"Failed to save branches: {e}", extra={'request_id': 'PERSISTENCE'})

    async def load_from_file(self):
        """Загрузить ветки из JSON файла"""
        import json
        import os

        if not os.path.exists(self.STORAGE_FILE):
            logger.info("No branches file found, starting fresh", extra={'request_id': 'PERSISTENCE'})
            return

        async with self._lock:
            try:
                with open(self.STORAGE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for user_id_str, user_data in data.get("users", {}).items():
                    user_id = int(user_id_str)
                    self.user_branches[user_id] = {}
                    self.current_branch[user_id] = user_data.get("current_branch")
                    self.user_last_activity[user_id] = user_data.get("last_activity", time.time())

                    for bid, branch_data in user_data.get("branches", {}).items():
                        branch = ConversationBranch.from_dict(branch_data)
                        self.user_branches[user_id][bid] = branch

                logger.info(
                    f"BRANCHES_LOADED: {len(self.user_branches)} users loaded from {self.STORAGE_FILE}",
                    extra={'request_id': 'PERSISTENCE'}
                )
            except Exception as e:
                logger.error(f"Failed to load branches: {e}", extra={'request_id': 'PERSISTENCE'})

    async def get_or_create_branch(self, user_id: int) -> ConversationBranch:
        """Получить текущую ветку или создать новую"""
        async with self._lock:
            # Обновляем время активности
            self._update_activity(user_id)

            # Инициализация для нового пользователя
            if user_id not in self.user_branches:
                self.user_branches[user_id] = {}

            # Если нет текущей ветки - создаём
            if user_id not in self.current_branch or \
               self.current_branch[user_id] not in self.user_branches[user_id]:
                branch = await self._create_branch_internal(user_id, "Основная")
                self.current_branch[user_id] = branch.id
                return branch

            return self.user_branches[user_id][self.current_branch[user_id]]

    async def _create_branch_internal(self, user_id: int, name: str = "") -> ConversationBranch:
        """Внутренний метод создания ветки (без блокировки)"""
        branch_id = str(uuid.uuid4())[:8]
        branch = ConversationBranch(branch_id, name)
        self.user_branches[user_id][branch_id] = branch

        logger.info(
            f"BRANCH_CREATED: user={user_id}, branch={branch_id}, name={name}",
            extra={'request_id': f'USER_{user_id}'}
        )
        return branch

    async def create_new_branch(self, user_id: int, name: str = "") -> ConversationBranch:
        """Создать новую ветку и переключиться на неё"""
        async with self._lock:
            if user_id not in self.user_branches:
                self.user_branches[user_id] = {}

            # Проверяем лимит веток
            if len(self.user_branches[user_id]) >= self.MAX_BRANCHES_PER_USER:
                # Удаляем самую старую неактивную ветку
                oldest = min(
                    self.user_branches[user_id].values(),
                    key=lambda b: b.updated_at
                )
                del self.user_branches[user_id][oldest.id]
                logger.info(
                    f"BRANCH_REMOVED: user={user_id}, branch={oldest.id} (limit reached)",
                    extra={'request_id': f'USER_{user_id}'}
                )

            branch = await self._create_branch_internal(user_id, name)
            self.current_branch[user_id] = branch.id
            return branch

    async def switch_branch(self, user_id: int, branch_id: str) -> Optional[ConversationBranch]:
        """Переключиться на другую ветку"""
        async with self._lock:
            if user_id not in self.user_branches:
                return None

            if branch_id not in self.user_branches[user_id]:
                return None

            self.current_branch[user_id] = branch_id
            branch = self.user_branches[user_id][branch_id]

            logger.info(
                f"BRANCH_SWITCH: user={user_id}, branch={branch_id}",
                extra={'request_id': f'USER_{user_id}'}
            )
            return branch

    async def reset_current_branch(self, user_id: int) -> Optional[ConversationBranch]:
        """Сбросить (очистить) текущую ветку"""
        async with self._lock:
            if user_id not in self.current_branch:
                return None

            branch_id = self.current_branch[user_id]
            if branch_id not in self.user_branches.get(user_id, {}):
                return None

            branch = self.user_branches[user_id][branch_id]
            branch.clear()

            logger.info(
                f"BRANCH_RESET: user={user_id}, branch={branch_id}",
                extra={'request_id': f'USER_{user_id}'}
            )
            return branch

    async def delete_branch(self, user_id: int, branch_id: str) -> bool:
        """Удалить ветку"""
        async with self._lock:
            if user_id not in self.user_branches:
                return False

            if branch_id not in self.user_branches[user_id]:
                return False

            # Нельзя удалить текущую ветку если она единственная
            if len(self.user_branches[user_id]) == 1:
                return False

            del self.user_branches[user_id][branch_id]

            # Если удалили текущую - переключаемся на другую
            if self.current_branch.get(user_id) == branch_id:
                other_branch = next(iter(self.user_branches[user_id].values()))
                self.current_branch[user_id] = other_branch.id

            logger.info(
                f"BRANCH_DELETED: user={user_id}, branch={branch_id}",
                extra={'request_id': f'USER_{user_id}'}
            )
            return True

    async def get_branches(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить список веток пользователя"""
        async with self._lock:
            if user_id not in self.user_branches:
                return []

            current_id = self.current_branch.get(user_id)
            branches = []

            for branch in self.user_branches[user_id].values():
                info = branch.to_dict()
                info["is_current"] = (branch.id == current_id)
                branches.append(info)

            # Сортируем по времени обновления (новые первые)
            branches.sort(key=lambda b: b["updated_at"], reverse=True)
            return branches

    async def add_message_to_current(self, user_id: int, role: str, content: str):
        """Добавить сообщение в текущую ветку"""
        branch = await self.get_or_create_branch(user_id)
        branch.add_message(role, content)

    async def get_context_for_api(self, user_id: int, max_messages: int = 10) -> List[Dict[str, str]]:
        """Получить контекст диалога для отправки в API"""
        branch = await self.get_or_create_branch(user_id)
        return branch.get_context(max_messages)

    def get_stats(self) -> Dict[str, int]:
        """Статистика по веткам"""
        total_branches = sum(len(b) for b in self.user_branches.values())
        total_messages = sum(
            len(branch.messages)
            for user_branches in self.user_branches.values()
            for branch in user_branches.values()
        )
        return {
            "users_with_branches": len(self.user_branches),
            "total_branches": total_branches,
            "total_messages": total_messages
        }


# Глобальный менеджер веток
branch_manager = BranchManager()


# ============ [1] RATE LIMITER С TTL И ОЧИСТКОЙ ПАМЯТИ ============
class UserRateLimiter:
    """Rate limiter с TTL и автоматической очисткой неактивных пользователей"""

    def __init__(self, calls_limit: int = 5, period: int = 60, user_ttl: int = 3600):
        self.calls_limit = calls_limit
        self.period = period
        self.user_ttl = user_ttl  # Время жизни записи пользователя

        # Используем deque с ограничением размера вместо list
        self.user_requests: Dict[int, deque] = {}
        self.user_last_activity: Dict[int, float] = {}  # Для TTL
        self.lock = asyncio.Lock()

        # Задача очистки
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self):
        """Запуск фоновой задачи очистки"""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("UserRateLimiter cleanup task started")

    async def stop_cleanup_task(self):
        """Остановка задачи очистки"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _periodic_cleanup(self):
        """Периодическая очистка неактивных пользователей"""
        while True:
            try:
                await asyncio.sleep(300)  # Каждые 5 минут
                await self._cleanup_inactive_users()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}", extra={'request_id': 'CLEANUP'})

    async def _cleanup_inactive_users(self):
        """Очистка пользователей без активности > TTL"""
        async with self.lock:
            now = time.time()
            inactive_users = [
                user_id for user_id, last_activity in self.user_last_activity.items()
                if now - last_activity > self.user_ttl
            ]

            for user_id in inactive_users:
                del self.user_requests[user_id]
                del self.user_last_activity[user_id]

            if inactive_users:
                logger.info(
                    f"Cleaned up {len(inactive_users)} inactive users. "
                    f"Active users: {len(self.user_requests)}",
                    extra={'request_id': 'CLEANUP'}
                )

    async def is_allowed(self, user_id: int) -> bool:
        """Проверяет, может ли пользователь сделать запрос"""
        async with self.lock:
            now = time.time()

            # Инициализация для нового пользователя
            if user_id not in self.user_requests:
                self.user_requests[user_id] = deque(maxlen=self.calls_limit)

            # Обновляем время активности
            self.user_last_activity[user_id] = now

            # Очищаем старые запросы (sliding window)
            user_deque = self.user_requests[user_id]
            while user_deque and now - user_deque[0] >= self.period:
                user_deque.popleft()

            # Проверяем лимит
            if len(user_deque) < self.calls_limit:
                user_deque.append(now)
                return True

            # Логируем rate limit
            logger.warning(
                f"RATE_LIMIT: user_id={user_id}, requests_in_window={len(user_deque)}",
                extra={'request_id': f'USER_{user_id}'}
            )
            return False

    def get_remaining_time(self, user_id: int) -> float:
        """Возвращает время до сброса лимита"""
        if user_id not in self.user_requests or not self.user_requests[user_id]:
            return 0

        oldest_request = self.user_requests[user_id][0]
        remaining = self.period - (time.time() - oldest_request)
        return max(0, remaining)

    def get_active_users_count(self) -> int:
        """Количество активных пользователей"""
        return len(self.user_requests)


# Глобальный rate limiter
user_rate_limiter = UserRateLimiter(
    calls_limit=config.RATE_LIMIT_PER_USER,
    period=config.RATE_LIMIT_PERIOD,
    user_ttl=config.USER_TTL_SECONDS
)


# ============ [2] API RATE LIMITER С ПУБЛИЧНЫМ СОСТОЯНИЕМ ============
class APIRateLimiter:
    """Ограничитель запросов к API с публичным доступом к состоянию"""

    def __init__(self, max_concurrent: int = 10, name: str = "API"):
        self.max_concurrent = max_concurrent  # Публичное поле!
        self.name = name
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._acquired_count = 0
        self._lock = asyncio.Lock()

    @property
    def available_slots(self) -> int:
        """Публичный доступ к количеству свободных слотов"""
        return self.max_concurrent - self._acquired_count

    @property
    def used_slots(self) -> int:
        """Количество занятых слотов"""
        return self._acquired_count

    @property
    def utilization_percent(self) -> float:
        """Процент использования"""
        return (self._acquired_count / self.max_concurrent) * 100 if self.max_concurrent > 0 else 0

    async def acquire(self):
        """Получить разрешение на запрос"""
        await self.semaphore.acquire()
        async with self._lock:
            self._acquired_count += 1

            # Логируем высокую нагрузку
            if self.utilization_percent >= 80:
                logger.warning(
                    f"HIGH_LOAD: {self.name} utilization={self.utilization_percent:.1f}%",
                    extra={'request_id': 'SYSTEM'}
                )

    def release(self):
        """Освободить семафор"""
        self.semaphore.release()
        # Используем синхронный декремент (безопасно для release)
        self._acquired_count = max(0, self._acquired_count - 1)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


# Лимитеры для каждого API
gigachat_limiter = APIRateLimiter(config.MAX_CONCURRENT_API_CALLS // 3, "GigaChat")
groq_limiter = APIRateLimiter(config.MAX_CONCURRENT_API_CALLS // 3, "Groq")
mistral_limiter = APIRateLimiter(config.MAX_CONCURRENT_API_CALLS // 3, "Mistral")


# ============ CIRCUIT BREAKER ============
class CircuitState(Enum):
    """Состояния Circuit Breaker"""
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # Отказ, запросы блокируются
    HALF_OPEN = "half_open"  # Тестовый режим


class CircuitBreaker:
    """
    Circuit Breaker для защиты от каскадных сбоев.

    States:
    - CLOSED: Нормальная работа, запросы проходят
    - OPEN: Сервис недоступен, запросы сразу отклоняются
    - HALF_OPEN: Пробуем восстановить, пропускаем ограниченное число запросов
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_requests: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._half_open_allowed = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_available(self) -> bool:
        """Проверка доступности без изменения состояния"""
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            # Проверяем, не пора ли перейти в HALF_OPEN
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                return True  # Можно попробовать
            return False
        # HALF_OPEN
        return self._half_open_allowed > 0

    async def acquire(self) -> bool:
        """
        Попытка получить разрешение на запрос.
        Returns: True если запрос разрешён, False если circuit открыт
        """
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Проверяем timeout для перехода в HALF_OPEN
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_allowed = self.half_open_requests
                    self._success_count = 0
                    logger.info(
                        f"CIRCUIT_HALF_OPEN: {self.name} entering half-open state",
                        extra={'request_id': 'CIRCUIT'}
                    )
                else:
                    return False

            # HALF_OPEN state
            if self._half_open_allowed > 0:
                self._half_open_allowed -= 1
                return True

            return False

    async def record_success(self):
        """Записать успешный запрос"""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_requests:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(
                        f"CIRCUIT_CLOSED: {self.name} recovered",
                        extra={'request_id': 'CIRCUIT'}
                    )
            elif self._state == CircuitState.CLOSED:
                # Сбрасываем счётчик ошибок при успехе
                self._failure_count = max(0, self._failure_count - 1)

    async def record_failure(self):
        """Записать неудачный запрос"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Сразу открываем при ошибке в half-open
                self._state = CircuitState.OPEN
                logger.warning(
                    f"CIRCUIT_OPEN: {self.name} failed in half-open, reopening",
                    extra={'request_id': 'CIRCUIT'}
                )
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"CIRCUIT_OPEN: {self.name} opened after {self._failure_count} failures",
                        extra={'request_id': 'CIRCUIT'}
                    )

    def get_status(self) -> Dict[str, Any]:
        """Получить статус для мониторинга"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "is_available": self.is_available,
            "last_failure": self._last_failure_time
        }


# Circuit Breakers для каждого AI провайдера
gigachat_circuit = CircuitBreaker("GigaChat", failure_threshold=5, recovery_timeout=30.0)
groq_circuit = CircuitBreaker("Groq", failure_threshold=5, recovery_timeout=30.0)
mistral_circuit = CircuitBreaker("Mistral", failure_threshold=5, recovery_timeout=30.0)


# ============ GRACEFUL SHUTDOWN ============
class GracefulShutdown:
    """
    Менеджер graceful shutdown для корректного завершения работы.

    Состояния:
    - running: нормальная работа
    - shutting_down: завершение, новые запросы отклоняются
    - stopped: полная остановка
    """

    def __init__(self, drain_timeout: float = 30.0):
        self.drain_timeout = drain_timeout
        self._is_shutting_down = False
        self._is_ready = False
        self._shutdown_event = asyncio.Event()
        self._active_requests = 0
        self._lock = asyncio.Lock()

    @property
    def is_ready(self) -> bool:
        """Готовность принимать запросы (для readiness probe)"""
        return self._is_ready and not self._is_shutting_down

    @property
    def is_alive(self) -> bool:
        """Бот жив (для liveness probe)"""
        return True  # Если код выполняется, бот жив

    @property
    def is_shutting_down(self) -> bool:
        return self._is_shutting_down

    def set_ready(self, ready: bool = True):
        """Установить готовность"""
        self._is_ready = ready
        logger.info(
            f"READINESS: {'ready' if ready else 'not ready'}",
            extra={'request_id': 'LIFECYCLE'}
        )

    async def start_request(self) -> bool:
        """
        Начать обработку запроса.
        Returns: True если можно обрабатывать, False если shutdown
        """
        async with self._lock:
            if self._is_shutting_down:
                return False
            self._active_requests += 1
            return True

    async def end_request(self):
        """Завершить обработку запроса"""
        async with self._lock:
            self._active_requests = max(0, self._active_requests - 1)

    async def initiate_shutdown(self):
        """Начать graceful shutdown"""
        logger.info("SHUTDOWN_INITIATED: Starting graceful shutdown", extra={'request_id': 'SHUTDOWN'})

        self._is_shutting_down = True
        self._is_ready = False

        # Ждём завершения активных запросов
        start_time = time.time()
        while self._active_requests > 0:
            elapsed = time.time() - start_time
            if elapsed >= self.drain_timeout:
                logger.warning(
                    f"SHUTDOWN_TIMEOUT: {self._active_requests} requests still active after {self.drain_timeout}s",
                    extra={'request_id': 'SHUTDOWN'}
                )
                break

            logger.info(
                f"SHUTDOWN_DRAIN: Waiting for {self._active_requests} active requests, elapsed={elapsed:.1f}s",
                extra={'request_id': 'SHUTDOWN'}
            )
            await asyncio.sleep(1.0)

        logger.info("SHUTDOWN_COMPLETE: All requests drained", extra={'request_id': 'SHUTDOWN'})
        self._shutdown_event.set()

    def get_status(self) -> Dict[str, Any]:
        """Статус для мониторинга"""
        return {
            "is_ready": self.is_ready,
            "is_alive": self.is_alive,
            "is_shutting_down": self._is_shutting_down,
            "active_requests": self._active_requests
        }


# Глобальный менеджер shutdown
shutdown_manager = GracefulShutdown(drain_timeout=30.0)


# ============ [3] БЕЗОПАСНЫЙ SSL КОНТЕКСТ ============
def create_ssl_context(verify: bool = True) -> ssl.SSLContext:
    """Создание SSL контекста с проверкой сертификатов"""

    if not verify or config.DISABLE_SSL_VERIFY:
        # Только для разработки! Логируем предупреждение
        logger.warning(
            "SSL_INSECURE: Certificate verification disabled! "
            "This is insecure and should not be used in production.",
            extra={'request_id': 'SECURITY'}
        )
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    # Production: используем certifi или системные сертификаты
    try:
        import certifi
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        logger.info("SSL: Using certifi certificates", extra={'request_id': 'SECURITY'})
    except ImportError:
        ssl_context = ssl.create_default_context()
        logger.info("SSL: Using system certificates", extra={'request_id': 'SECURITY'})

    return ssl_context


# Глобальные SSL контексты
ssl_context_secure = create_ssl_context(verify=True)
ssl_context_insecure = create_ssl_context(verify=False)  # Для GigaChat если нужно


# ============ [6] RETRY ЛОГИКА С EXPONENTIAL BACKOFF ============
import random

class RetryableError(Exception):
    """Ошибка, после которой можно повторить запрос"""
    pass


# Статусы, при которых БЕЗОПАСНО повторять запрос
SAFE_RETRY_STATUSES = (
    429,  # Too Many Requests (rate limit)
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
)

# Статусы, при которых НЕ нужно повторять (клиентские ошибки)
NON_RETRYABLE_STATUSES = (
    400,  # Bad Request
    401,  # Unauthorized
    403,  # Forbidden
    404,  # Not Found
    405,  # Method Not Allowed
    422,  # Unprocessable Entity
)


def is_safe_to_retry(status_code: int) -> bool:
    """Проверка, безопасно ли повторять запрос с данным статусом"""
    if status_code in NON_RETRYABLE_STATUSES:
        return False
    return status_code in SAFE_RETRY_STATUSES or status_code >= 500


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 2,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    jitter: bool = True,
    request_id: str = "N/A"
) -> Any:
    """
    Выполнение функции с повторными попытками, exponential backoff и jitter.

    Safe retry policy:
    - Retry на 5xx ошибки (сервер)
    - Retry на 429 (rate limit)
    - Retry на сетевые ошибки и таймауты
    - НЕ retry на 4xx (клиентские ошибки, кроме 429)

    Args:
        func: Async функция для выполнения
        max_retries: Максимальное количество повторов
        base_delay: Базовая задержка (удваивается с каждой попыткой)
        max_delay: Максимальная задержка между попытками
        jitter: Добавлять случайный jitter для предотвращения thundering herd
        request_id: ID запроса для логирования
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()

        except aiohttp.ClientResponseError as e:
            # Проверяем, безопасно ли повторять
            if is_safe_to_retry(e.status) and attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)

                # Добавляем jitter (±25%)
                if jitter:
                    delay = delay * (0.75 + random.random() * 0.5)

                logger.warning(
                    f"RETRY: attempt={attempt + 1}/{max_retries + 1}, "
                    f"status={e.status}, delay={delay:.2f}s, safe_retry=True",
                    extra={'request_id': request_id}
                )
                await metrics.record_retry()
                await asyncio.sleep(delay)
                last_exception = e
            else:
                # Не безопасно повторять - логируем и выбрасываем
                if e.status in NON_RETRYABLE_STATUSES:
                    logger.warning(
                        f"NO_RETRY: status={e.status} is non-retryable (client error)",
                        extra={'request_id': request_id}
                    )
                raise

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            # Сетевые ошибки и таймауты - безопасно повторять
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)

                if jitter:
                    delay = delay * (0.75 + random.random() * 0.5)

                logger.warning(
                    f"RETRY: attempt={attempt + 1}/{max_retries + 1}, "
                    f"error={type(e).__name__}, delay={delay:.2f}s",
                    extra={'request_id': request_id}
                )
                await metrics.record_retry()
                await asyncio.sleep(delay)
                last_exception = e
            else:
                raise

    if last_exception:
        raise last_exception


# ============ ОПТИМИЗИРОВАННЫЕ СЕССИИ ============
class AIClientPool:
    """Пул клиентов для API"""

    def __init__(self):
        self.gigachat_session: Optional[aiohttp.ClientSession] = None
        self.groq_session: Optional[aiohttp.ClientSession] = None
        self.mistral_session: Optional[aiohttp.ClientSession] = None
        self.connector: Optional[aiohttp.TCPConnector] = None

    async def init(self):
        """Инициализация пула соединений"""
        self.connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30
        )

        # GigaChat сессия (может требовать отключения SSL проверки)
        self.gigachat_session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_CHAT),
            connector_owner=False
        )

        self.groq_session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_CHAT)
        )

        self.mistral_session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_CHAT)
        )

        logger.info("AI Client Pool initialized", extra={'request_id': 'STARTUP'})

    async def close(self):
        """Закрытие всех сессий"""
        for session in [self.gigachat_session, self.groq_session, self.mistral_session]:
            if session and not session.closed:
                await session.close()

        if self.connector:
            await self.connector.close()

        logger.info("AI Client Pool closed", extra={'request_id': 'SHUTDOWN'})


# Глобальный пул
ai_pool = AIClientPool()


# ============ КЭШ ТОКЕНОВ GIGACHAT ============
gigachat_token_cache = {"token": None, "expires_at": 0}


async def get_gigachat_token(request_id: str = "N/A") -> Optional[str]:
    """Получает токен для GigaChat с retry"""
    if gigachat_token_cache["token"] and time.time() < gigachat_token_cache["expires_at"]:
        return gigachat_token_cache["token"]

    logger.info("Fetching new GigaChat token...", extra={'request_id': request_id})

    async def fetch_token():
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        rq_uid = str(uuid.uuid4())

        headers = {
            "Authorization": f"Bearer {config.SBER_API_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
            "RqUID": rq_uid,
            "Accept": "application/json"
        }

        data = {"scope": "GIGACHAT_API_PERS"}

        # [7] Используем короткий таймаут для OAuth
        async with ai_pool.gigachat_session.post(
            url,
            headers=headers,
            data=data,
            ssl=ssl_context_insecure,  # GigaChat может требовать это
            timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_OAUTH)
        ) as response:

            if response.status == 200:
                result = await response.json()
                access_token = result.get("access_token")

                if access_token:
                    gigachat_token_cache["token"] = access_token
                    gigachat_token_cache["expires_at"] = time.time() + 3500  # ~58 минут
                    logger.info("GigaChat token obtained", extra={'request_id': request_id})
                    return access_token

            response.raise_for_status()

        return None

    try:
        return await retry_with_backoff(fetch_token, max_retries=2, request_id=request_id)
    except Exception as e:
        logger.error(f"Failed to get GigaChat token: {e}", extra={'request_id': request_id})
        return None


# ============ [5] КЭШ ОТВЕТОВ С УЧЁТОМ КОНТЕКСТА ============
class RequestType(Enum):
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"


class ContextAwareCache:
    """Кэш ответов с учётом контекста, TTL и периодической очисткой"""

    CLEANUP_INTERVAL = 300  # 5 минут

    def __init__(self, max_size: int = 500, ttl: int = 3600):
        self.cache: Dict[str, tuple] = {}  # key -> (result, timestamp)
        self.max_size = max_size
        self.ttl = ttl
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self):
        """Запуск фоновой задачи очистки"""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Cache cleanup task started", extra={'request_id': 'STARTUP'})

    async def stop_cleanup_task(self):
        """Остановка задачи очистки"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _periodic_cleanup(self):
        """Периодическая очистка устаревших записей"""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}", extra={'request_id': 'CLEANUP'})

    async def _cleanup_expired(self):
        """Очистка устаревших записей"""
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self.cache.items()
                if now - timestamp >= self.ttl
            ]

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                logger.info(
                    f"CACHE_TTL_CLEANUP: Removed {len(expired_keys)} expired entries. "
                    f"Remaining: {len(self.cache)}",
                    extra={'request_id': 'CLEANUP'}
                )

    def _create_key(
        self,
        question: str,
        request_type: RequestType = RequestType.TEXT,
        file_hash: Optional[str] = None,
        image_hash: Optional[str] = None,
        context_hash: Optional[str] = None
    ) -> str:
        """Создание уникального ключа с учётом полного контекста (включая историю диалога)"""
        components = [
            question,
            request_type.value,
            file_hash or "",
            image_hash or "",
            context_hash or ""  # Хэш контекста диалога
        ]
        composite = "|".join(components)
        return hashlib.sha256(composite.encode()).hexdigest()

    @staticmethod
    def compute_context_hash(context_messages: Optional[List[Dict[str, str]]]) -> Optional[str]:
        """Вычислить хэш контекста для использования в ключе кэша"""
        if not context_messages:
            return None
        # Создаём хэш из последних сообщений контекста
        context_str = str(context_messages[-5:])  # Последние 5 сообщений
        return hashlib.md5(context_str.encode()).hexdigest()[:12]

    async def get(
        self,
        question: str,
        request_type: RequestType = RequestType.TEXT,
        file_hash: Optional[str] = None,
        image_hash: Optional[str] = None,
        context_hash: Optional[str] = None
    ) -> Optional[Any]:
        """Получить из кэша"""
        key = self._create_key(question, request_type, file_hash, image_hash, context_hash)

        async with self._lock:
            if key in self.cache:
                result, timestamp = self.cache[key]

                # Проверяем TTL
                if time.time() - timestamp < self.ttl:
                    logger.info(
                        f"CACHE_HIT: type={request_type.value}",
                        extra={'request_id': 'CACHE'}
                    )
                    return result
                else:
                    # Устаревшая запись
                    del self.cache[key]

        return None

    async def set(
        self,
        question: str,
        result: Any,
        request_type: RequestType = RequestType.TEXT,
        file_hash: Optional[str] = None,
        image_hash: Optional[str] = None,
        context_hash: Optional[str] = None
    ):
        """Сохранить в кэш"""
        key = self._create_key(question, request_type, file_hash, image_hash, context_hash)

        async with self._lock:
            # Очистка при переполнении (удаляем самые старые)
            if len(self.cache) >= self.max_size:
                # Удаляем 10% самых старых записей
                sorted_keys = sorted(
                    self.cache.keys(),
                    key=lambda k: self.cache[k][1]
                )
                for old_key in sorted_keys[:len(sorted_keys) // 10 + 1]:
                    del self.cache[old_key]

                logger.info(
                    f"CACHE_CLEANUP: removed {len(sorted_keys) // 10 + 1} entries",
                    extra={'request_id': 'CACHE'}
                )

            self.cache[key] = (result, time.time())

    async def get_or_compute(
        self,
        question: str,
        compute_func: Callable,
        request_type: RequestType = RequestType.TEXT,
        file_hash: Optional[str] = None,
        image_hash: Optional[str] = None,
        context_hash: Optional[str] = None
    ) -> Any:
        """Получить из кэша или вычислить"""
        cached = await self.get(question, request_type, file_hash, image_hash, context_hash)
        if cached is not None:
            return cached

        result = await compute_func(question)
        await self.set(question, result, request_type, file_hash, image_hash, context_hash)
        return result

    def get_stats(self) -> Dict[str, int]:
        return {
            "entries": len(self.cache),
            "max_size": self.max_size,
            "backend": "memory"
        }


# ============ REDIS CACHE ADAPTER (Optional) ============
class RedisCacheAdapter:
    """
    Redis-based cache adapter для горизонтального масштабирования.
    Использует тот же интерфейс что и ContextAwareCache.

    Включается через REDIS_ENABLED=true в .env
    """

    def __init__(self, redis_url: str, ttl: int = 3600):
        self.redis_url = redis_url
        self.ttl = ttl
        self._client = None
        self._connected = False

    async def connect(self):
        """Подключение к Redis"""
        try:
            import aioredis
            self._client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Проверяем соединение
            await self._client.ping()
            self._connected = True
            logger.info(f"Redis connected: {self.redis_url}", extra={'request_id': 'STARTUP'})
        except ImportError:
            logger.warning("aioredis not installed, falling back to memory cache", extra={'request_id': 'STARTUP'})
            self._connected = False
        except Exception as e:
            logger.error(f"Redis connection failed: {e}", extra={'request_id': 'STARTUP'})
            self._connected = False

    async def close(self):
        """Закрытие соединения"""
        if self._client:
            await self._client.close()
            self._connected = False

    def _create_key(
        self,
        question: str,
        request_type: RequestType = RequestType.TEXT,
        file_hash: Optional[str] = None,
        image_hash: Optional[str] = None,
        context_hash: Optional[str] = None
    ) -> str:
        """Создание ключа для Redis"""
        components = [question, request_type.value, file_hash or "", image_hash or "", context_hash or ""]
        composite = "|".join(components)
        return f"bot:cache:{hashlib.sha256(composite.encode()).hexdigest()}"

    async def get(
        self,
        question: str,
        request_type: RequestType = RequestType.TEXT,
        file_hash: Optional[str] = None,
        image_hash: Optional[str] = None,
        context_hash: Optional[str] = None
    ) -> Optional[Any]:
        """Получить из Redis"""
        if not self._connected:
            return None

        key = self._create_key(question, request_type, file_hash, image_hash, context_hash)
        try:
            data = await self._client.get(key)
            if data:
                logger.info(f"REDIS_CACHE_HIT: type={request_type.value}", extra={'request_id': 'CACHE'})
                return json.loads(data)
        except Exception as e:
            logger.error(f"Redis get error: {e}", extra={'request_id': 'CACHE'})

        return None

    async def set(
        self,
        question: str,
        result: Any,
        request_type: RequestType = RequestType.TEXT,
        file_hash: Optional[str] = None,
        image_hash: Optional[str] = None,
        context_hash: Optional[str] = None
    ):
        """Сохранить в Redis"""
        if not self._connected:
            return

        key = self._create_key(question, request_type, file_hash, image_hash, context_hash)
        try:
            await self._client.setex(key, self.ttl, json.dumps(result))
        except Exception as e:
            logger.error(f"Redis set error: {e}", extra={'request_id': 'CACHE'})

    async def get_or_compute(
        self,
        question: str,
        compute_func: Callable,
        request_type: RequestType = RequestType.TEXT,
        file_hash: Optional[str] = None,
        image_hash: Optional[str] = None,
        context_hash: Optional[str] = None
    ) -> Any:
        """Получить из кэша или вычислить"""
        cached = await self.get(question, request_type, file_hash, image_hash, context_hash)
        if cached is not None:
            return cached

        result = await compute_func(question)
        await self.set(question, result, request_type, file_hash, image_hash, context_hash)
        return result

    async def start_cleanup_task(self):
        """Redis управляет TTL автоматически, cleanup не нужен"""
        pass

    async def stop_cleanup_task(self):
        """Закрываем соединение"""
        await self.close()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "backend": "redis",
            "connected": self._connected,
            "url": self.redis_url[:20] + "..." if len(self.redis_url) > 20 else self.redis_url
        }


# Создаём кэш в зависимости от конфигурации
def create_cache():
    """Factory для создания кэша (memory или redis)"""
    if config.REDIS_ENABLED:
        logger.info("Using Redis cache backend", extra={'request_id': 'STARTUP'})
        return RedisCacheAdapter(config.REDIS_URL, config.REDIS_CACHE_TTL)
    else:
        logger.info("Using in-memory cache backend", extra={'request_id': 'STARTUP'})
        return ContextAwareCache(max_size=500)


response_cache = create_cache()


# ============ [7] ФУНКЦИИ API С ДИФФЕРЕНЦИРОВАННЫМИ ТАЙМАУТАМИ ============
def calculate_max_tokens(question: str, request_type: RequestType = RequestType.TEXT) -> int:
    """Автоматический расчёт max_tokens в зависимости от типа запроса"""
    question_len = len(question)

    if request_type == RequestType.IMAGE:
        return 1000
    elif request_type == RequestType.FILE:
        return 1500
    elif question_len < 100:
        return 500
    elif question_len < 500:
        return 1000
    else:
        return 1500


async def query_gigachat_optimized(
    question: str,
    request_id: str = "N/A",
    request_type: RequestType = RequestType.TEXT,
    context_messages: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Оптимизированный запрос к GigaChat с retry, Circuit Breaker и контекстом диалога"""
    start_time = time.time()

    # Circuit Breaker check
    if not await gigachat_circuit.acquire():
        return {
            "service": "GigaChat",
            "success": False,
            "response": "GigaChat временно недоступен (circuit open)",
            "error": "Circuit breaker open",
            "response_time": 0
        }

    async with gigachat_limiter:
        async def make_request():
            access_token = await get_gigachat_token(request_id)
            if not access_token:
                return {
                    "service": "GigaChat",
                    "success": False,
                    "response": "Не удалось авторизоваться в GigaChat",
                    "error": "Auth failed",
                    "response_time": time.time() - start_time
                }

            url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # [7] Адаптивные max_tokens
            max_tokens = calculate_max_tokens(question, request_type)

            # Формируем messages с контекстом
            if context_messages:
                messages = context_messages + [{"role": "user", "content": question}]
            else:
                messages = [{"role": "user", "content": question}]

            data = {
                "model": "GigaChat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": max_tokens
            }

            # [7] Таймаут зависит от типа запроса
            timeout = config.TIMEOUT_VISION if request_type == RequestType.IMAGE else config.TIMEOUT_CHAT

            async with ai_pool.gigachat_session.post(
                url,
                headers=headers,
                json=data,
                ssl=ssl_context_insecure,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:

                response_time = time.time() - start_time

                if response.status == 200:
                    result = await response.json()
                    choices = result.get("choices", [])

                    if choices and len(choices) > 0:
                        content = choices[0].get("message", {}).get("content", "Пустой ответ")

                        await metrics.record_request("GigaChat", True, response_time)

                        return {
                            "service": "GigaChat",
                            "success": True,
                            "response": content,
                            "error": None,
                            "response_time": response_time
                        }

                elif response.status == 401:
                    gigachat_token_cache["token"] = None
                    logger.warning(
                        f"GigaChat 401 - token invalidated",
                        extra={'request_id': request_id}
                    )

                elif response.status in (502, 503, 504):
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status
                    )

                error_text = await response.text()
                await metrics.record_request("GigaChat", False, response_time, f"HTTP {response.status}")

                return {
                    "service": "GigaChat",
                    "success": False,
                    "response": f"Ошибка GigaChat API: {response.status}",
                    "error": error_text[:200],
                    "response_time": response_time
                }

        try:
            result = await retry_with_backoff(make_request, max_retries=2, request_id=request_id)
            # Circuit Breaker: записываем результат
            if result.get("success"):
                await gigachat_circuit.record_success()
            else:
                await gigachat_circuit.record_failure()
            return result

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            await metrics.record_request("GigaChat", False, response_time, "Timeout")
            await gigachat_circuit.record_failure()
            logger.error(
                f"TIMEOUT: GigaChat, elapsed={response_time:.2f}s",
                extra={'request_id': request_id}
            )
            return {
                "service": "GigaChat",
                "success": False,
                "response": "Таймаут запроса GigaChat",
                "error": "Timeout",
                "response_time": response_time
            }
        except Exception as e:
            response_time = time.time() - start_time
            await metrics.record_request("GigaChat", False, response_time, str(type(e).__name__))
            await gigachat_circuit.record_failure()
            logger.error(
                f"ERROR: GigaChat, error={e}",
                extra={'request_id': request_id}
            )
            return {
                "service": "GigaChat",
                "success": False,
                "response": f"Ошибка сети GigaChat: {str(e)[:200]}",
                "error": str(e),
                "response_time": response_time
            }


async def query_groq_optimized(
    question: str,
    request_id: str = "N/A",
    request_type: RequestType = RequestType.TEXT,
    context_messages: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Оптимизированный запрос к Groq API с retry, Circuit Breaker и контекстом диалога"""
    start_time = time.time()

    # Circuit Breaker check
    if not await groq_circuit.acquire():
        return {
            "service": "Groq",
            "success": False,
            "response": "Groq временно недоступен (circuit open)",
            "error": "Circuit breaker open",
            "response_time": 0
        }

    async with groq_limiter:
        if not config.GROQ_API_KEY:
            return {
                "service": "Groq",
                "success": False,
                "response": "API ключ Groq не настроен",
                "error": "Missing API key",
                "response_time": 0
            }

        async def make_request():
            url = "https://api.groq.com/openai/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }

            max_tokens = calculate_max_tokens(question, request_type)

            # Формируем messages с контекстом
            if context_messages:
                messages = context_messages + [{"role": "user", "content": question}]
            else:
                messages = [{"role": "user", "content": question}]

            data = {
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": max_tokens,
                "top_p": 0.95
            }

            async with ai_pool.groq_session.post(
                url,
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_CHAT)
            ) as response:

                response_time = time.time() - start_time

                if response.status == 200:
                    result = await response.json()

                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0].get("message", {}).get("content", "").strip()

                        if content:
                            await metrics.record_request("Groq", True, response_time)
                            return {
                                "service": "Groq",
                                "success": True,
                                "response": content,
                                "error": None,
                                "response_time": response_time
                            }

                elif response.status == 429:
                    await metrics.record_request("Groq", False, response_time, "Rate limit exceeded")
                    logger.warning(
                        f"RATE_LIMIT: Groq API rate limit exceeded",
                        extra={'request_id': request_id}
                    )
                    return {
                        "service": "Groq",
                        "success": False,
                        "response": "Превышен лимит запросов к Groq API",
                        "error": "Rate limit exceeded",
                        "response_time": response_time
                    }

                elif response.status in (502, 503, 504):
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status
                    )

                error_text = await response.text()
                await metrics.record_request("Groq", False, response_time, f"HTTP {response.status}")

                return {
                    "service": "Groq",
                    "success": False,
                    "response": f"Ошибка Groq API: {response.status}",
                    "error": error_text[:200],
                    "response_time": response_time
                }

        try:
            result = await retry_with_backoff(make_request, max_retries=2, request_id=request_id)
            # Circuit Breaker: записываем результат
            if result.get("success"):
                await groq_circuit.record_success()
            else:
                await groq_circuit.record_failure()
            return result

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            await metrics.record_request("Groq", False, response_time, "Timeout")
            await groq_circuit.record_failure()
            logger.error(
                f"TIMEOUT: Groq, elapsed={response_time:.2f}s",
                extra={'request_id': request_id}
            )
            return {
                "service": "Groq",
                "success": False,
                "response": "Таймаут запроса Groq",
                "error": "Timeout",
                "response_time": response_time
            }
        except Exception as e:
            response_time = time.time() - start_time
            await metrics.record_request("Groq", False, response_time, str(type(e).__name__))
            await groq_circuit.record_failure()
            logger.error(
                f"ERROR: Groq, error={e}",
                extra={'request_id': request_id}
            )
            return {
                "service": "Groq",
                "success": False,
                "response": f"Ошибка сети Groq: {str(e)[:200]}",
                "error": str(e),
                "response_time": response_time
            }


async def query_mistral_optimized(
    question: str,
    request_id: str = "N/A",
    request_type: RequestType = RequestType.TEXT,
    context_messages: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Оптимизированный запрос к Mistral AI API с retry, Circuit Breaker и контекстом диалога"""
    start_time = time.time()

    # Circuit Breaker check
    if not await mistral_circuit.acquire():
        return {
            "service": "Mistral",
            "success": False,
            "response": "Mistral временно недоступен (circuit open)",
            "error": "Circuit breaker open",
            "response_time": 0
        }

    async with mistral_limiter:
        if not config.MISTRAL_API_KEY:
            return {
                "service": "Mistral",
                "success": False,
                "response": "API ключ Mistral не настроен",
                "error": "Missing API key",
                "response_time": 0
            }

        async def make_request():
            url = "https://api.mistral.ai/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {config.MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            }

            max_tokens = calculate_max_tokens(question, request_type)

            # Формируем messages с контекстом
            if context_messages:
                messages = context_messages + [{"role": "user", "content": question}]
            else:
                messages = [{"role": "user", "content": question}]

            data = {
                "model": "mistral-small-latest",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": max_tokens,
                "top_p": 0.95
            }

            async with ai_pool.mistral_session.post(
                url,
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=config.TIMEOUT_CHAT)
            ) as response:

                response_time = time.time() - start_time

                if response.status == 200:
                    result = await response.json()

                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0].get("message", {}).get("content", "").strip()

                        if content:
                            await metrics.record_request("Mistral", True, response_time)
                            return {
                                "service": "Mistral",
                                "success": True,
                                "response": content,
                                "error": None,
                                "response_time": response_time
                            }

                elif response.status == 429:
                    await metrics.record_request("Mistral", False, response_time, "Rate limit exceeded")
                    logger.warning(
                        f"RATE_LIMIT: Mistral API rate limit exceeded",
                        extra={'request_id': request_id}
                    )
                    return {
                        "service": "Mistral",
                        "success": False,
                        "response": "Превышен лимит запросов к Mistral API",
                        "error": "Rate limit",
                        "response_time": response_time
                    }

                elif response.status in (502, 503, 504):
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status
                    )

                error_text = await response.text()
                await metrics.record_request("Mistral", False, response_time, f"HTTP {response.status}")

                return {
                    "service": "Mistral",
                    "success": False,
                    "response": f"Ошибка Mistral API: {response.status}",
                    "error": error_text[:200],
                    "response_time": response_time
                }

        try:
            result = await retry_with_backoff(make_request, max_retries=2, request_id=request_id)
            # Circuit Breaker: записываем результат
            if result.get("success"):
                await mistral_circuit.record_success()
            else:
                await mistral_circuit.record_failure()
            return result

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            await metrics.record_request("Mistral", False, response_time, "Timeout")
            await mistral_circuit.record_failure()
            logger.error(
                f"TIMEOUT: Mistral, elapsed={response_time:.2f}s",
                extra={'request_id': request_id}
            )
            return {
                "service": "Mistral",
                "success": False,
                "response": "Таймаут запроса Mistral",
                "error": "Timeout",
                "response_time": response_time
            }
        except Exception as e:
            response_time = time.time() - start_time
            await metrics.record_request("Mistral", False, response_time, str(type(e).__name__))
            await mistral_circuit.record_failure()
            logger.error(
                f"ERROR: Mistral, error={e}",
                extra={'request_id': request_id}
            )
            return {
                "service": "Mistral",
                "success": False,
                "response": f"Ошибка сети Mistral: {str(e)[:200]}",
                "error": str(e),
                "response_time": response_time
            }


# ============ ОСНОВНАЯ ФУНКЦИЯ ЗАПРОСА ============
async def query_all_ais(
    question: str,
    request_id: str = "N/A",
    request_type: RequestType = RequestType.TEXT,
    file_hash: Optional[str] = None,
    image_hash: Optional[str] = None,
    context_messages: Optional[List[Dict[str, str]]] = None
) -> List[Dict[str, Any]]:
    """Отправляет запрос ко всем трем нейросетям одновременно с контекстом диалога"""

    # Вычисляем хэш контекста для ключа кэша
    context_hash = ContextAwareCache.compute_context_hash(context_messages)

    logger.info(
        f"REQUEST: type={request_type.value}, question_len={len(question)}, "
        f"context_len={len(context_messages) if context_messages else 0}, context_hash={context_hash}",
        extra={'request_id': request_id}
    )

    async def compute_results(q):
        tasks = [
            query_gigachat_optimized(q, request_id, request_type, context_messages),
            query_groq_optimized(q, request_id, request_type, context_messages),
            query_mistral_optimized(q, request_id, request_type, context_messages)
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            processed_results = []
            for i, result in enumerate(results):
                service_name = ["GigaChat", "Groq", "Mistral"][i]

                if isinstance(result, Exception):
                    logger.error(
                        f"EXCEPTION: service={service_name}, error={result}",
                        extra={'request_id': request_id}
                    )
                    processed_results.append({
                        "service": service_name,
                        "success": False,
                        "response": f"Исключение: {str(result)[:200]}",
                        "error": str(result),
                        "response_time": 0
                    })
                else:
                    processed_results.append(result)

            # Логируем итоговый результат
            success_count = sum(1 for r in processed_results if r.get("success"))
            logger.info(
                f"COMPLETED: success={success_count}/3",
                extra={'request_id': request_id}
            )

            return processed_results

        except Exception as e:
            logger.error(f"FATAL: query_all_ais error={e}", extra={'request_id': request_id})
            return []

    return await response_cache.get_or_compute(
        question,
        compute_results,
        request_type,
        file_hash,
        image_hash,
        context_hash
    )


async def query_all_ais_with_progress(
    question: str,
    request_id: str = "N/A",
    request_type: RequestType = RequestType.TEXT,
    context_messages: Optional[List[Dict[str, str]]] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    timeout: float = 60.0
) -> List[Dict[str, Any]]:
    """
    Запрос ко всем AI с partial progress updates.

    Возвращает результаты по мере готовности через callback on_progress.
    Имеет общий timeout - если не все AI ответили, возвращает partial results.

    Args:
        question: Вопрос пользователя
        request_id: ID запроса
        request_type: Тип запроса
        context_messages: Контекст диалога
        on_progress: Callback вызываемый при получении каждого результата
        timeout: Общий таймаут для всех запросов

    Returns:
        Список результатов (может быть неполным при timeout)
    """
    logger.info(
        f"REQUEST_WITH_PROGRESS: type={request_type.value}, timeout={timeout}s",
        extra={'request_id': request_id}
    )

    # Создаём задачи с именами сервисов
    tasks_map = {
        "GigaChat": asyncio.create_task(
            query_gigachat_optimized(question, request_id, request_type, context_messages)
        ),
        "Groq": asyncio.create_task(
            query_groq_optimized(question, request_id, request_type, context_messages)
        ),
        "Mistral": asyncio.create_task(
            query_mistral_optimized(question, request_id, request_type, context_messages)
        )
    }

    results = []
    completed_services = set()
    start_time = time.time()

    try:
        # Используем as_completed для получения результатов по мере готовности
        for coro in asyncio.as_completed(list(tasks_map.values()), timeout=timeout):
            try:
                result = await coro

                # Определяем какой сервис завершился
                service_name = result.get("service", "Unknown")
                completed_services.add(service_name)
                results.append(result)

                # Вызываем callback с прогрессом
                if on_progress:
                    progress_info = {
                        "service": service_name,
                        "success": result.get("success", False),
                        "completed": len(completed_services),
                        "total": 3,
                        "elapsed": time.time() - start_time
                    }
                    try:
                        if asyncio.iscoroutinefunction(on_progress):
                            await on_progress(progress_info)
                        else:
                            on_progress(progress_info)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}", extra={'request_id': request_id})

                logger.info(
                    f"PROGRESS: {service_name} completed ({len(completed_services)}/3)",
                    extra={'request_id': request_id}
                )

            except Exception as e:
                logger.error(f"Task error: {e}", extra={'request_id': request_id})

    except asyncio.TimeoutError:
        # Timeout - собираем partial results
        elapsed = time.time() - start_time
        logger.warning(
            f"PARTIAL_TIMEOUT: {len(completed_services)}/3 completed in {elapsed:.1f}s",
            extra={'request_id': request_id}
        )

        # Добавляем timeout errors для незавершённых сервисов
        for service_name, task in tasks_map.items():
            if service_name not in completed_services:
                task.cancel()
                results.append({
                    "service": service_name,
                    "success": False,
                    "response": f"Таймаут ({timeout}s) - сервис не ответил вовремя",
                    "error": "Timeout",
                    "response_time": timeout
                })

    # Сортируем результаты в стандартном порядке
    service_order = {"GigaChat": 0, "Groq": 1, "Mistral": 2}
    results.sort(key=lambda r: service_order.get(r.get("service", ""), 99))

    success_count = sum(1 for r in results if r.get("success"))
    logger.info(
        f"COMPLETED_WITH_PROGRESS: success={success_count}/3, partial={len(results) < 3}",
        extra={'request_id': request_id}
    )

    return results


# ============ ФУНКЦИИ ДЛЯ РАБОТЫ С ФАЙЛАМИ ============
def create_log_file(results: List[Dict], question: str, username: str, request_id: str) -> io.BytesIO:
    """Создает лог-файл с результатами всех нейросетей"""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_content = f"""ЛОГ ОТВЕТОВ ОТ ТРЕХ НЕЙРОСЕТЕЙ
Дата: {timestamp}
Request ID: {request_id}
Вопрос: {question}
Пользователь: {username}

{'='*80}

"""

    for i, result in enumerate(results, 1):
        service = result.get("service", f"Сервис {i}")
        success = result.get("success", False)
        response = result.get("response", "Нет ответа")
        error = result.get("error")
        response_time = result.get("response_time", 0)

        log_content += f"\n{'#'*40}\n"
        log_content += f"СЕРВИС: {service}\n"
        log_content += f"Статус: {'УСПЕШНО' if success else 'ОШИБКА'}\n"
        log_content += f"Время: {response_time:.2f} секунд\n"

        if error:
            log_content += f"Ошибка: {error}\n"

        log_content += f"\nОТВЕТ:\n{'-'*40}\n"
        log_content += f"{response}\n"

        log_content += f"\n{'#'*40}\n\n"

    successful = sum(1 for r in results if r.get("success", False))
    failed = len(results) - successful

    log_content += f"\n{'='*80}\n"
    log_content += "СТАТИСТИКА:\n"
    log_content += f"Всего сервисов: {len(results)}\n"
    log_content += f"Успешно: {successful}\n"
    log_content += f"Ошибок: {failed}\n"

    filename = f"ai_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request_id[:8]}.txt"
    file_stream = io.BytesIO(log_content.encode('utf-8'))
    file_stream.name = filename
    file_stream.seek(0)

    return file_stream


# ============ PRIORITY QUEUE SUPPORT ============
from dataclasses import dataclass, field
import heapq


class UserTier(Enum):
    """Уровни пользователей для приоритизации"""
    FREE = 2      # Низкий приоритет
    PREMIUM = 1   # Высокий приоритет
    ADMIN = 0     # Максимальный приоритет


@dataclass(order=True)
class PriorityRequest:
    """Запрос с приоритетом для очереди"""
    priority: int
    timestamp: float = field(compare=False)
    user_id: int = field(compare=False)
    question: str = field(compare=False)
    message: Any = field(compare=False)
    request_id: str = field(compare=False)


def get_premium_users() -> set:
    """Получить список premium пользователей из конфига"""
    if not config.PREMIUM_USER_IDS:
        return set()
    try:
        return {int(uid.strip()) for uid in config.PREMIUM_USER_IDS.split(",") if uid.strip()}
    except ValueError:
        return set()


def get_user_tier(user_id: int) -> UserTier:
    """Определить tier пользователя"""
    premium_users = get_premium_users()
    if user_id in premium_users:
        return UserTier.PREMIUM
    return UserTier.FREE


# ============ [4][8] ОЧЕРЕДЬ С BACKPRESSURE И АДАПТИВНЫМИ ВОРКЕРАМИ ============
class AdaptiveRequestQueue:
    """Очередь с backpressure, приоритетами и адаптивными воркерами"""

    def __init__(self, maxsize: int = 1000, min_workers: int = 2, max_workers: int = 20):
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=maxsize)
        self.maxsize = maxsize
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.workers: List[asyncio.Task] = []
        self.is_running = False
        self._scaling_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def add_request(
        self,
        user_id: int,
        question: str,
        message: types.Message,
        request_id: str
    ) -> tuple[bool, str]:
        """
        Добавить запрос в очередь с backpressure и приоритетами

        Returns:
            (success, message): успех и сообщение для пользователя
        """
        # Проверка graceful shutdown
        if shutdown_manager.is_shutting_down:
            logger.info(
                f"REQUEST_REJECTED: Bot is shutting down",
                extra={'request_id': request_id}
            )
            return False, "Бот перезапускается. Попробуйте через минуту."

        queue_size = self.queue.qsize()

        # [4] Backpressure: отказ при перегрузке
        if queue_size >= self.maxsize * 0.95:  # 95% заполнения
            await metrics.record_queue_overflow()
            logger.warning(
                f"QUEUE_FULL: size={queue_size}/{self.maxsize}, rejecting request",
                extra={'request_id': request_id}
            )
            return False, "Сервер перегружен. Попробуйте через минуту."

        # Предупреждение при высокой нагрузке
        if queue_size >= self.maxsize * 0.7:  # 70% заполнения
            logger.warning(
                f"QUEUE_HIGH: size={queue_size}/{self.maxsize}",
                extra={'request_id': request_id}
            )

        try:
            # Определяем приоритет пользователя
            user_tier = get_user_tier(user_id)
            priority = user_tier.value

            # Создаём PriorityRequest
            priority_request = PriorityRequest(
                priority=priority,
                timestamp=time.time(),
                user_id=user_id,
                question=question,
                message=message,
                request_id=request_id
            )

            await self.queue.put(priority_request)

            # Расчёт ETA с учётом приоритета
            position = self._estimate_position(priority, queue_size)
            eta_seconds = self._calculate_eta(position)

            # Формируем сообщение с учётом tier
            tier_label = ""
            if user_tier == UserTier.PREMIUM:
                tier_label = "⭐ "
            elif user_tier == UserTier.ADMIN:
                tier_label = "👑 "

            if position > 10:
                status_msg = f"{tier_label}Запрос в очереди. Позиция: ~{position}. Ожидание: ~{eta_seconds // 60} мин."
            else:
                status_msg = f"{tier_label}Запрос принят. Позиция: ~{position}. Ожидание: ~{eta_seconds} сек."

            logger.info(
                f"REQUEST_QUEUED: user={user_id}, tier={user_tier.name}, priority={priority}, position=~{position}",
                extra={'request_id': request_id}
            )

            return True, status_msg

        except asyncio.QueueFull:
            await metrics.record_queue_overflow()
            return False, "Очередь переполнена. Попробуйте позже."

    def _estimate_position(self, priority: int, queue_size: int) -> int:
        """
        Оценка позиции в очереди с учётом приоритета.
        Более приоритетные запросы обходят менее приоритетные.
        """
        if queue_size == 0:
            return 1

        # Грубая оценка: предполагаем равномерное распределение приоритетов
        # ADMIN (0) будет первым, PREMIUM (1) после админов, FREE (2) в конце
        if priority == 0:  # ADMIN
            return 1  # Почти сразу
        elif priority == 1:  # PREMIUM
            return max(1, queue_size // 3)  # В первой трети очереди
        else:  # FREE
            return queue_size  # В конце очереди

    def _calculate_eta(self, position: int) -> int:
        """
        Расчёт ETA на основе позиции и количества воркеров.
        """
        active_workers = len([w for w in self.workers if not w.done()])
        if active_workers == 0:
            active_workers = self.min_workers

        # Среднее время обработки одного запроса ~6 секунд
        avg_processing_time = 6.0

        # ETA = (position / active_workers) * avg_time
        eta = (position / active_workers) * avg_processing_time
        return max(1, int(eta))

    async def worker(self, worker_id: int, bot: Bot):
        """Воркер для обработки запросов из приоритетной очереди"""
        logger.info(f"Worker {worker_id} started", extra={'request_id': 'WORKER'})

        while self.is_running:
            try:
                # Таймаут чтобы воркер мог проверить is_running
                try:
                    priority_request: PriorityRequest = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Распаковка PriorityRequest
                user_id = priority_request.user_id
                question = priority_request.question
                message = priority_request.message
                request_id = priority_request.request_id
                wait_time = time.time() - priority_request.timestamp

                logger.info(
                    f"Worker {worker_id} processing request (priority={priority_request.priority}, waited={wait_time:.1f}s)",
                    extra={'request_id': request_id}
                )

                # Уведомляем пользователя о начале обработки
                status_message = None
                try:
                    status_message = await bot.send_message(
                        chat_id=user_id,
                        text="⏳ Обрабатываю запрос... (0/3)"
                    )
                except Exception:
                    pass

                # Сохраняем вопрос пользователя в ветку диалога
                await branch_manager.add_message_to_current(user_id, "user", question)

                # Получаем контекст диалога для AI
                context_messages = await branch_manager.get_context_for_api(user_id)

                # Callback для partial progress updates
                async def on_progress(progress: Dict[str, Any]):
                    """Обновляем статус сообщение при получении каждого ответа"""
                    if status_message:
                        completed = progress.get("completed", 0)
                        total = progress.get("total", 3)
                        service = progress.get("service", "")
                        success = progress.get("success", False)
                        elapsed = progress.get("elapsed", 0)

                        status_icon = "✅" if success else "❌"
                        progress_bar = "●" * completed + "○" * (total - completed)

                        try:
                            await bot.edit_message_text(
                                chat_id=user_id,
                                message_id=status_message.message_id,
                                text=f"⏳ Обрабатываю запрос... ({completed}/{total})\n"
                                     f"{progress_bar}\n"
                                     f"{status_icon} {service} ({elapsed:.1f}s)"
                            )
                        except Exception:
                            pass  # Игнорируем ошибки редактирования

                # Получаем результат с контекстом и progress updates
                results = await query_all_ais_with_progress(
                    question,
                    request_id,
                    context_messages=context_messages,
                    on_progress=on_progress,
                    timeout=90.0  # Общий таймаут 90 секунд
                )

                # Сохраняем успешные ответы в ветку диалога
                successful_responses = []
                for r in results:
                    if r.get("success"):
                        successful_responses.append(f"[{r['service']}]: {r['response'][:200]}")

                if successful_responses:
                    # Сохраняем сводный ответ в ветку
                    combined_response = "\n---\n".join(successful_responses)
                    await branch_manager.add_message_to_current(
                        user_id, "assistant", combined_response[:1000]
                    )

                # Создаем файл с результатами
                username = message.from_user.username or f"user_{user_id}"
                log_file = create_log_file(results, question, username, request_id)

                # Отправляем пользователю
                await bot.send_document(
                    chat_id=user_id,
                    document=types.BufferedInputFile(
                        log_file.read(),
                        filename=log_file.name
                    ),
                    caption=f"Ответы от 3 нейросетей\nВопрос: {question[:50]}..."
                )

                # Финальное сообщение со статистикой
                successful = sum(1 for r in results if r.get("success", False))
                partial = any(r.get("error") == "Timeout" for r in results)

                final_text = f"✅ Готово! Успешных ответов: {successful}/3"
                if partial:
                    final_text += "\n⚠️ Некоторые сервисы не ответили вовремя (partial results)"

                # Удаляем status message и отправляем финальный
                if status_message:
                    try:
                        await bot.delete_message(chat_id=user_id, message_id=status_message.message_id)
                    except Exception:
                        pass

                await bot.send_message(chat_id=user_id, text=final_text)

                logger.info(
                    f"Worker {worker_id} completed request",
                    extra={'request_id': request_id}
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Worker {worker_id} error: {e}",
                    extra={'request_id': request_id if 'request_id' in dir() else 'WORKER'}
                )
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"Ошибка при обработке запроса. Попробуйте позже."
                    )
                except Exception:
                    pass
            finally:
                try:
                    self.queue.task_done()
                except ValueError:
                    pass

        logger.info(f"Worker {worker_id} stopped", extra={'request_id': 'WORKER'})

    async def _auto_scale_workers(self, bot: Bot):
        """
        [8] Автоматическое масштабирование воркеров (scale up + scale down).

        Алгоритм:
        - Scale up: при высокой нагрузке (queue > threshold)
        - Scale down: при низкой нагрузке (queue < threshold && idle workers)
        - Cooldown: минимум 30с между изменениями
        """
        last_scale_time = 0
        scale_cooldown = 30  # секунд между масштабированиями
        idle_threshold = 60  # секунд простоя для scale down

        # Отслеживаем время простоя каждого воркера
        worker_last_active: Dict[int, float] = {}

        while self.is_running:
            try:
                await asyncio.sleep(10)  # Проверка каждые 10 секунд

                now = time.time()
                queue_size = self.queue.qsize()

                # Подсчёт активных воркеров
                active_workers = [w for w in self.workers if not w.done()]
                current_workers = len(active_workers)

                # Обновляем метрики
                prom_metrics.set_queue_size(queue_size)
                prom_metrics.set_active_workers(current_workers)

                # Проверяем cooldown
                if now - last_scale_time < scale_cooldown:
                    continue

                # Вычисляем целевое количество воркеров
                queue_utilization = queue_size / self.maxsize

                if queue_utilization > 0.5:  # > 50% очереди
                    target_workers = self.max_workers
                elif queue_utilization > 0.3:  # 30-50%
                    target_workers = min(self.max_workers, max(self.min_workers, current_workers + 2))
                elif queue_utilization > 0.1:  # 10-30%
                    target_workers = max(self.min_workers, queue_size // 3 + 2)
                elif queue_size > 0:  # 1-10%
                    target_workers = max(self.min_workers, queue_size + 1)
                else:  # Очередь пуста
                    target_workers = self.min_workers

                # Scale UP
                if current_workers < target_workers:
                    async with self._lock:
                        workers_to_add = target_workers - current_workers
                        for i in range(workers_to_add):
                            worker_id = len(self.workers)
                            worker_task = asyncio.create_task(self.worker(worker_id, bot))
                            self.workers.append(worker_task)
                            worker_last_active[worker_id] = now

                        logger.info(
                            f"SCALE_UP: workers {current_workers} -> {len(self.workers)}, "
                            f"queue_size={queue_size}, utilization={queue_utilization:.1%}",
                            extra={'request_id': 'AUTOSCALE'}
                        )
                        last_scale_time = now

                # Scale DOWN (при низкой нагрузке и idle workers)
                elif current_workers > target_workers and queue_size == 0:
                    # Проверяем, есть ли воркеры, которые простаивают достаточно долго
                    workers_to_remove = current_workers - target_workers

                    # Находим idle воркеров (не обрабатывали задачи > idle_threshold секунд)
                    # Так как воркеры работают бесконечно, мы не можем их остановить напрямую
                    # Вместо этого логируем информацию для ручного управления
                    if workers_to_remove > 0:
                        logger.info(
                            f"SCALE_DOWN_RECOMMENDED: {current_workers} -> {target_workers} workers, "
                            f"queue_size={queue_size}, idle workers can be reduced",
                            extra={'request_id': 'AUTOSCALE'}
                        )
                        # Примечание: в Kubernetes это обрабатывается HPA
                        # В standalone режиме воркеры остаются до рестарта

                # Очистка завершённых воркеров из списка
                async with self._lock:
                    self.workers = [w for w in self.workers if not w.done()]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Autoscale error: {e}", extra={'request_id': 'AUTOSCALE'})

    async def start_workers(self, num_workers: int, bot: Bot):
        """Запуск воркеров"""
        self.is_running = True

        # Запускаем начальных воркеров
        for i in range(num_workers):
            worker_task = asyncio.create_task(self.worker(i, bot))
            self.workers.append(worker_task)

        # Запускаем автомасштабирование
        self._scaling_task = asyncio.create_task(self._auto_scale_workers(bot))

        logger.info(
            f"Started {num_workers} workers with autoscaling",
            extra={'request_id': 'STARTUP'}
        )

    async def stop_workers(self, drain_timeout: float = 30.0):
        """Остановка воркеров с drain очереди"""
        logger.info(
            f"QUEUE_DRAIN: Starting, queue_size={self.queue.qsize()}, timeout={drain_timeout}s",
            extra={'request_id': 'SHUTDOWN'}
        )

        # Останавливаем автомасштабирование
        if self._scaling_task:
            self._scaling_task.cancel()
            try:
                await self._scaling_task
            except asyncio.CancelledError:
                pass

        # Ждём drain очереди
        start_time = time.time()
        while not self.queue.empty():
            elapsed = time.time() - start_time
            if elapsed >= drain_timeout:
                remaining = self.queue.qsize()
                logger.warning(
                    f"QUEUE_DRAIN_TIMEOUT: {remaining} items remaining after {drain_timeout}s",
                    extra={'request_id': 'SHUTDOWN'}
                )
                break

            logger.info(
                f"QUEUE_DRAIN: Waiting, remaining={self.queue.qsize()}, elapsed={elapsed:.1f}s",
                extra={'request_id': 'SHUTDOWN'}
            )
            await asyncio.sleep(1.0)

        # Сигнализируем воркерам об остановке
        self.is_running = False

        # Останавливаем воркеров
        for worker in self.workers:
            worker.cancel()

        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        logger.info("All workers stopped", extra={'request_id': 'SHUTDOWN'})

    def get_stats(self) -> Dict[str, Any]:
        return {
            "queue_size": self.queue.qsize(),
            "max_size": self.maxsize,
            "utilization_percent": (self.queue.qsize() / self.maxsize) * 100,
            "active_workers": len([w for w in self.workers if not w.done()]),
            "total_workers": len(self.workers)
        }


# Создаем очередь
request_queue = AdaptiveRequestQueue(
    maxsize=config.QUEUE_MAX_SIZE,
    min_workers=config.MIN_WORKERS,
    max_workers=config.MAX_WORKERS
)


# ============ INPUT VALIDATION ============
class InputValidator:
    """Валидация и санитизация входных данных"""

    @staticmethod
    def validate_question(text: str) -> tuple[bool, str]:
        """
        Валидация текста вопроса.
        Returns: (is_valid, error_message)
        """
        if not text or not text.strip():
            return False, "Пустой вопрос"

        text = text.strip()

        if len(text) < config.MIN_QUESTION_LENGTH:
            return False, f"Вопрос слишком короткий (минимум {config.MIN_QUESTION_LENGTH} символа)"

        if len(text) > config.MAX_QUESTION_LENGTH:
            return False, f"Вопрос слишком длинный (максимум {config.MAX_QUESTION_LENGTH} символов)"

        return True, ""

    @staticmethod
    def sanitize_question(text: str) -> str:
        """
        Базовая санитизация текста.
        Удаляет потенциально опасные конструкции.
        """
        text = text.strip()

        # Удаляем null bytes
        text = text.replace('\x00', '')

        # Удаляем контрольные символы (кроме \n, \t)
        text = ''.join(char for char in text if char >= ' ' or char in '\n\t')

        return text

    @staticmethod
    def validate_file_size(size_bytes: int) -> tuple[bool, str]:
        """Валидация размера файла"""
        max_size = config.MAX_FILE_SIZE_KB * 1024
        if size_bytes > max_size:
            return False, f"Файл слишком большой (максимум {config.MAX_FILE_SIZE_KB} KB)"
        return True, ""

    @staticmethod
    def truncate_context(messages: List[Dict[str, str]], max_messages: int = None) -> List[Dict[str, str]]:
        """Обрезка контекста до максимального размера"""
        max_msg = max_messages or config.MAX_CONTEXT_MESSAGES
        if len(messages) > max_msg:
            return messages[-max_msg:]
        return messages


input_validator = InputValidator()


# ============ ОБРАБОТЧИКИ БОТА ============
async def handle_message_with_queue(message: types.Message, bot: Bot):
    """Обработка сообщения через очередь с валидацией"""
    user_id = message.from_user.id
    request_id = str(uuid.uuid4())[:12]

    # Санитизация и валидация входных данных
    question = input_validator.sanitize_question(message.text or "")
    is_valid, error_msg = input_validator.validate_question(question)

    if not is_valid:
        logger.warning(
            f"INPUT_VALIDATION_FAILED: user={user_id}, reason={error_msg}",
            extra={'request_id': request_id}
        )
        await message.answer(error_msg)
        return

    # Проверяем rate limit
    if not await user_rate_limiter.is_allowed(user_id):
        remaining = user_rate_limiter.get_remaining_time(user_id)
        await message.answer(f"Слишком много запросов. Попробуйте через {remaining:.0f} секунд.")
        return

    # Сохраняем сообщение пользователя в текущую ветку
    await branch_manager.add_message_to_current(user_id, "user", question)

    # Получаем текущую ветку для отображения
    branch = await branch_manager.get_or_create_branch(user_id)

    # Добавляем в очередь
    success, status_msg = await request_queue.add_request(user_id, question, message, request_id)

    # Показываем статус с информацией о ветке
    branch_info = f"\n[Ветка: {branch.name}]" if branch else ""
    await message.answer(status_msg + branch_info)


# ============ ОПТИМИЗИРОВАННЫЙ ЗАПУСК ============
async def on_startup(bot: Bot):
    """Запуск при старте бота"""
    logger.info("=" * 50, extra={'request_id': 'STARTUP'})
    logger.info("STARTING BOT v3.2 (Enterprise + Observability)", extra={'request_id': 'STARTUP'})
    logger.info("=" * 50, extra={'request_id': 'STARTUP'})

    # Запуск observability HTTP сервера
    await observability_server.start()

    # Инициализация пула соединений
    await ai_pool.init()

    # Запуск очистки rate limiter
    await user_rate_limiter.start_cleanup_task()

    # Запуск воркеров
    await request_queue.start_workers(num_workers=config.MIN_WORKERS, bot=bot)

    # Загружаем сохранённые ветки диалогов
    await branch_manager.load_from_file()

    # Запуск очистки веток
    await branch_manager.start_cleanup_task()

    # Подключение к Redis (если enabled) и запуск очистки кэша
    if hasattr(response_cache, 'connect'):
        await response_cache.connect()
    await response_cache.start_cleanup_task()

    # Устанавливаем готовность
    shutdown_manager.set_ready(True)

    logger.info("Bot started successfully", extra={'request_id': 'STARTUP'})


async def on_shutdown(bot: Bot):
    """Остановка при завершении с graceful drain"""
    logger.info("Stopping bot...", extra={'request_id': 'SHUTDOWN'})

    # 1. Инициируем graceful shutdown (ждём drain активных запросов)
    await shutdown_manager.initiate_shutdown()

    # 2. Останавливаем воркеры (с drain очереди)
    await request_queue.stop_workers()

    # 3. Останавливаем очистку rate limiter, branches и cache
    await user_rate_limiter.stop_cleanup_task()
    await branch_manager.stop_cleanup_task()
    await response_cache.stop_cleanup_task()

    # 4. Сохраняем ветки диалогов
    await branch_manager.save_to_file()
    logger.info("Branches saved to file", extra={'request_id': 'SHUTDOWN'})

    # 5. Закрываем пул соединений
    await ai_pool.close()

    # 6. Останавливаем observability сервер
    await observability_server.stop()

    # 7. Выводим финальную статистику
    stats = metrics.get_stats()
    circuit_status = {
        "gigachat": gigachat_circuit.get_status(),
        "groq": groq_circuit.get_status(),
        "mistral": mistral_circuit.get_status()
    }
    logger.info(f"FINAL_STATS: {stats}", extra={'request_id': 'SHUTDOWN'})
    logger.info(f"CIRCUIT_STATUS: {circuit_status}", extra={'request_id': 'SHUTDOWN'})

    logger.info("Bot stopped gracefully", extra={'request_id': 'SHUTDOWN'})


async def check_rate_limit(user_id: int, message: types.Message) -> bool:
    """Проверка rate limit для пользователя"""
    if not await user_rate_limiter.is_allowed(user_id):
        remaining = user_rate_limiter.get_remaining_time(user_id)
        await message.answer(f"Слишком много запросов. Попробуйте через {remaining:.0f} секунд.")
        return False
    return True


async def main_optimized():
    """Оптимизированный запуск бота"""

    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not configured!", extra={'request_id': 'STARTUP'})
        return

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем обработчики жизненного цикла
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # ============ КОМАНДЫ ============

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        """Команда /start"""
        welcome = """
Бот трех нейросетей v2.0 (Production-grade)

Отправьте любой вопрос и получите ответы от:
1. GigaChat (Sber AI)
2. Groq (Llama)
3. Mistral AI

Все ответы придут в одном TXT файле!

<b>Основные команды:</b>
/start - это сообщение
/status - проверить доступность нейросетей
/test - тестовый запрос
/info - информация о системе
/stats - статистика работы

<b>Управление ветками диалога:</b>
/new [имя] - создать новую ветку (сброс контекста)
/reset - очистить текущую ветку
/branches - список всех веток
/switch [id] - переключиться на ветку
/branch - текущая ветка
/delete [id] - удалить ветку
"""
        await message.answer(welcome)
        logger.info(
            f"User {message.from_user.id} started bot",
            extra={'request_id': f'USER_{message.from_user.id}'}
        )

    @dp.message(Command("status"))
    async def cmd_status(message: types.Message):
        """Проверка статуса"""
        if not await check_rate_limit(message.from_user.id, message):
            return

        request_id = str(uuid.uuid4())[:12]
        await message.answer("Проверяю нейросети...")

        test_results = await query_all_ais("Ответь 'ok'", request_id)

        status_msg = "Статус нейросетей:\n\n"
        for result in test_results:
            service = result.get("service", "Unknown")
            success = result.get("success", False)
            time_taken = result.get("response_time", 0)

            emoji = "+" if success else "-"
            status_msg += f"[{emoji}] {service}: ({time_taken:.2f}с)\n"

        await message.answer(status_msg)

    @dp.message(Command("test"))
    async def cmd_test(message: types.Message):
        """Тестовый запрос"""
        if not await check_rate_limit(message.from_user.id, message):
            return

        request_id = str(uuid.uuid4())[:12]
        await message.answer("Отправляю тестовые запросы...")

        results = await query_all_ais("Привет! Как дела? Ответь кратко.", request_id)

        username = message.from_user.username or f"user_{message.from_user.id}"
        log_file = create_log_file(results, "Тестовый запрос: Привет!", username, request_id)

        await message.answer_document(
            types.BufferedInputFile(log_file.read(), filename=log_file.name),
            caption="Тестовый запрос выполнен"
        )

        successful = sum(1 for r in results if r.get("success", False))
        await message.answer(f"Готово! Успешных ответов: {successful} из 3")

    @dp.message(Command("info"))
    async def cmd_info(message: types.Message):
        """Информация о системе"""
        if not await check_rate_limit(message.from_user.id, message):
            return

        queue_stats = request_queue.get_stats()
        cache_stats = response_cache.get_stats()
        branch_stats = branch_manager.get_stats()

        info_msg = "<b>Информация о системе:</b>\n\n"

        # Очередь
        info_msg += f"<b>Очередь:</b> {queue_stats['queue_size']}/{queue_stats['max_size']} "
        info_msg += f"({queue_stats['utilization_percent']:.1f}%)\n"
        info_msg += f"<b>Воркеры:</b> {queue_stats['active_workers']}/{queue_stats['total_workers']}\n\n"

        # Кэш
        info_msg += f"<b>Кэш:</b> {cache_stats['entries']}/{cache_stats['max_size']} записей\n\n"

        # Ветки диалога
        info_msg += f"<b>Ветки диалога:</b>\n"
        info_msg += f"- Пользователей: {branch_stats['users_with_branches']}\n"
        info_msg += f"- Всего веток: {branch_stats['total_branches']}\n"
        info_msg += f"- Всего сообщений: {branch_stats['total_messages']}\n\n"

        # API лимиты (публичные поля!)
        info_msg += "<b>Лимиты API (свободно):</b>\n"
        info_msg += f"- GigaChat: {gigachat_limiter.available_slots}/{gigachat_limiter.max_concurrent}\n"
        info_msg += f"- Groq: {groq_limiter.available_slots}/{groq_limiter.max_concurrent}\n"
        info_msg += f"- Mistral: {mistral_limiter.available_slots}/{mistral_limiter.max_concurrent}\n\n"

        # Rate limit
        info_msg += f"<b>Активных пользователей:</b> {user_rate_limiter.get_active_users_count()}\n"
        info_msg += f"<b>Ваш лимит:</b> {user_rate_limiter.calls_limit} запросов в {user_rate_limiter.period} сек"

        await message.answer(info_msg)

    @dp.message(Command("stats"))
    async def cmd_stats(message: types.Message):
        """Статистика работы бота"""
        if not await check_rate_limit(message.from_user.id, message):
            return

        stats = metrics.get_stats()

        stats_msg = "Статистика работы:\n\n"
        stats_msg += f"Всего запросов: {stats['requests_total']}\n"
        stats_msg += f"Успешных: {stats['requests_success']}\n"
        stats_msg += f"Неудачных: {stats['requests_failed']}\n"
        stats_msg += f"Таймаутов: {stats['requests_timeout']}\n"
        stats_msg += f"Rate-limited: {stats['requests_rate_limited']}\n"
        stats_msg += f"Переполнений очереди: {stats['queue_overflows']}\n"
        stats_msg += f"Повторных попыток: {stats['retries_total']}\n\n"

        stats_msg += f"Успешность: {stats['success_rate']:.1f}%\n\n"

        stats_msg += "Ошибки по сервисам:\n"
        for service, count in stats['errors_by_service'].items():
            stats_msg += f"- {service}: {count}\n"

        stats_msg += "\nСреднее время ответа:\n"
        for service, avg_time in stats['avg_response_times'].items():
            stats_msg += f"- {service}: {avg_time:.2f}с\n"

        await message.answer(stats_msg)

    # ============ КОМАНДЫ УПРАВЛЕНИЯ ВЕТКАМИ ============

    @dp.message(Command("new"))
    async def cmd_new_branch(message: types.Message):
        """Создать новую ветку диалога"""
        user_id = message.from_user.id

        # Извлекаем имя ветки из команды
        args = message.text.split(maxsplit=1)
        branch_name = args[1] if len(args) > 1 else ""

        branch = await branch_manager.create_new_branch(user_id, branch_name)

        await message.answer(
            f"Создана новая ветка диалога:\n"
            f"<b>ID:</b> <code>{branch.id}</code>\n"
            f"<b>Имя:</b> {branch.name}\n\n"
            f"Контекст сброшен. Начните новый диалог!"
        )

    @dp.message(Command("reset"))
    async def cmd_reset_branch(message: types.Message):
        """Сбросить текущую ветку"""
        user_id = message.from_user.id

        branch = await branch_manager.reset_current_branch(user_id)

        if branch:
            await message.answer(
                f"Ветка <b>{branch.name}</b> очищена.\n"
                f"История диалога сброшена."
            )
        else:
            await message.answer("Нет активной ветки для сброса.")

    @dp.message(Command("branches"))
    async def cmd_list_branches(message: types.Message):
        """Показать список веток"""
        user_id = message.from_user.id

        branches = await branch_manager.get_branches(user_id)

        if not branches:
            await message.answer("У вас пока нет веток диалога. Отправьте любой вопрос.")
            return

        msg = "<b>Ваши ветки диалога:</b>\n\n"

        for b in branches:
            current_marker = " [ТЕКУЩАЯ]" if b["is_current"] else ""
            msg += f"<code>{b['id']}</code>{current_marker}\n"
            msg += f"  Имя: {b['name']}\n"
            msg += f"  Сообщений: {b['message_count']}\n"
            msg += f"  Обновлена: {b['updated_at'][:16]}\n\n"

        msg += f"Всего веток: {len(branches)}/{branch_manager.MAX_BRANCHES_PER_USER}"

        await message.answer(msg)

    @dp.message(Command("switch"))
    async def cmd_switch_branch(message: types.Message):
        """Переключиться на другую ветку"""
        user_id = message.from_user.id

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "Укажите ID ветки: /switch <id>\n"
                "Список веток: /branches"
            )
            return

        branch_id = args[1].strip()
        branch = await branch_manager.switch_branch(user_id, branch_id)

        if branch:
            await message.answer(
                f"Переключено на ветку:\n"
                f"<b>ID:</b> <code>{branch.id}</code>\n"
                f"<b>Имя:</b> {branch.name}\n"
                f"<b>Сообщений:</b> {len(branch.messages)}"
            )
        else:
            await message.answer(
                f"Ветка <code>{branch_id}</code> не найдена.\n"
                "Список веток: /branches"
            )

    @dp.message(Command("branch"))
    async def cmd_current_branch(message: types.Message):
        """Показать текущую ветку"""
        user_id = message.from_user.id

        branch = await branch_manager.get_or_create_branch(user_id)

        msg = f"<b>Текущая ветка:</b>\n\n"
        msg += f"<b>ID:</b> <code>{branch.id}</code>\n"
        msg += f"<b>Имя:</b> {branch.name}\n"
        msg += f"<b>Сообщений:</b> {len(branch.messages)}\n"
        msg += f"<b>Создана:</b> {branch.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        msg += f"<b>Обновлена:</b> {branch.updated_at.strftime('%Y-%m-%d %H:%M')}\n"

        if branch.messages:
            msg += f"\n<b>Последние сообщения:</b>\n"
            for m in branch.messages[-3:]:
                role = "Вы" if m["role"] == "user" else "AI"
                content = m["content"][:50] + "..." if len(m["content"]) > 50 else m["content"]
                msg += f"  [{role}]: {content}\n"

        await message.answer(msg)

    @dp.message(Command("delete"))
    async def cmd_delete_branch(message: types.Message):
        """Удалить ветку"""
        user_id = message.from_user.id

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "Укажите ID ветки: /delete <id>\n"
                "Список веток: /branches"
            )
            return

        branch_id = args[1].strip()
        success = await branch_manager.delete_branch(user_id, branch_id)

        if success:
            await message.answer(f"Ветка <code>{branch_id}</code> удалена.")
        else:
            await message.answer(
                f"Не удалось удалить ветку <code>{branch_id}</code>.\n"
                "Возможно, она не существует или это единственная ветка."
            )

    @dp.message(F.text)
    async def handle_all_messages(message: types.Message):
        """Обработка всех текстовых сообщений"""
        if message.text.startswith('/'):
            return

        await handle_message_with_queue(message, bot)

    # ============ ЗАПУСК ============

    if config.USE_WEBHOOK:
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler
        from aiohttp import web

        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=config.WEBHOOK_SECRET
        )

        webhook_requests_handler.register(app, path=config.WEBHOOK_PATH)

        await bot.set_webhook(
            url=config.WEBHOOK_URL,
            secret_token=config.WEBHOOK_SECRET,
            drop_pending_updates=True
        )

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

        logger.info("Bot running in webhook mode", extra={'request_id': 'STARTUP'})
        await asyncio.Event().wait()
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Bot running in polling mode", extra={'request_id': 'STARTUP'})
        await dp.start_polling(bot)


# ============ ЗАПУСК ============
if __name__ == "__main__":
    try:
        asyncio.run(main_optimized())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user", extra={'request_id': 'SHUTDOWN'})
    except Exception as e:
        logger.error(f"Fatal error: {e}", extra={'request_id': 'FATAL'})
