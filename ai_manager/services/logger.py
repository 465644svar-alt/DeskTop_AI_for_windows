"""
Application Logger with metrics tracking
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass, asdict
from statistics import mean, median


@dataclass
class ResponseLogEntry:
    """Log entry for API response"""
    timestamp: str
    provider: str
    question: str
    response: str
    elapsed_time: float
    success: bool
    tokens_used: int = 0
    model: str = ""


@dataclass
class ErrorLogEntry:
    """Log entry for errors"""
    timestamp: str
    provider: str
    error: str
    details: str
    error_code: int = 0
    retryable: bool = False


@dataclass
class ProviderMetrics:
    """Metrics for a single provider"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time: float = 0.0
    total_tokens: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests * 100

    @property
    def avg_response_time(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_time / self.successful_requests

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.success_rate, 1),
            "avg_response_time": round(self.avg_response_time, 2),
            "total_tokens": self.total_tokens
        }


class AppLogger:
    """Application logger with response/error tracking and metrics"""

    def __init__(self, log_dir: str = "logs", max_responses: int = 1000, max_errors: int = 500):
        self.log_dir = log_dir
        self.session_start = datetime.now()

        # In-memory logs with size limits
        self.responses_log: deque = deque(maxlen=max_responses)
        self.errors_log: deque = deque(maxlen=max_errors)

        # Provider metrics
        self.metrics: Dict[str, ProviderMetrics] = {}

        # Recent response times for each provider (for trend analysis)
        self._response_times: Dict[str, deque] = {}

        # Create log directory
        os.makedirs(log_dir, exist_ok=True)

        # Setup file logging
        self._setup_file_logging()

    def _setup_file_logging(self):
        """Setup file-based logging"""
        log_file = os.path.join(
            self.log_dir,
            f"app_{self.session_start.strftime('%Y%m%d_%H%M%S')}.log"
        )

        # Create a new handler for this session
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
        )

        # Get root logger and add handler
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

        # Also log to console in debug mode
        if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)
            root_logger.addHandler(console_handler)

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Session started at {self.session_start}")

    def _ensure_metrics(self, provider: str):
        """Ensure metrics exist for provider"""
        if provider not in self.metrics:
            self.metrics[provider] = ProviderMetrics()
        if provider not in self._response_times:
            self._response_times[provider] = deque(maxlen=100)

    def log_response(
        self,
        provider: str,
        question: str,
        response: str,
        elapsed: float,
        success: bool = True,
        tokens_used: int = 0,
        model: str = ""
    ):
        """Log AI response and update metrics"""
        self._ensure_metrics(provider)

        entry = ResponseLogEntry(
            timestamp=datetime.now().isoformat(),
            provider=provider,
            question=question[:500],  # Truncate for log
            response=response[:5000] if success else response,  # Limit response size
            elapsed_time=elapsed,
            success=success,
            tokens_used=tokens_used,
            model=model
        )
        self.responses_log.append(asdict(entry))

        # Update metrics
        metrics = self.metrics[provider]
        metrics.total_requests += 1
        if success:
            metrics.successful_requests += 1
            metrics.total_time += elapsed
            metrics.total_tokens += tokens_used
            self._response_times[provider].append(elapsed)
        else:
            metrics.failed_requests += 1

        # Log to file
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"[{provider}] {status} | {elapsed:.2f}s | Q: {question[:100]}...")

    def log_error(
        self,
        provider: str,
        error: str,
        details: str = "",
        error_code: int = 0,
        retryable: bool = False
    ):
        """Log error with details"""
        entry = ErrorLogEntry(
            timestamp=datetime.now().isoformat(),
            provider=provider,
            error=error,
            details=details[:1000],
            error_code=error_code,
            retryable=retryable
        )
        self.errors_log.append(asdict(entry))

        self.logger.error(f"[{provider}] {error} | Code: {error_code} | {details[:200]}")

    def get_responses_log(self) -> List[dict]:
        """Get responses log"""
        return list(self.responses_log)

    def get_errors_log(self) -> List[dict]:
        """Get errors log"""
        return list(self.errors_log)

    def get_provider_metrics(self, provider: str) -> Optional[dict]:
        """Get metrics for a specific provider"""
        if provider in self.metrics:
            return self.metrics[provider].to_dict()
        return None

    def get_all_metrics(self) -> Dict[str, dict]:
        """Get metrics for all providers"""
        return {name: m.to_dict() for name, m in self.metrics.items()}

    def get_response_time_trend(self, provider: str) -> List[float]:
        """Get recent response times for trend analysis"""
        if provider in self._response_times:
            return list(self._response_times[provider])
        return []

    def export_logs(self, filepath: str, log_type: str = "all") -> bool:
        """Export logs to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write(f"AI Manager Log Export\n")
                f.write(f"Session: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Export: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")

                # Metrics summary
                f.write("PROVIDER METRICS\n")
                f.write("-" * 50 + "\n")
                for name, metrics in self.metrics.items():
                    m = metrics.to_dict()
                    f.write(f"\n{name}:\n")
                    f.write(f"  Requests: {m['total_requests']} (Success: {m['success_rate']:.1f}%)\n")
                    f.write(f"  Avg Time: {m['avg_response_time']:.2f}s\n")
                    f.write(f"  Tokens: {m['total_tokens']}\n")
                f.write("\n")

                if log_type in ["all", "responses"]:
                    f.write("=" * 70 + "\n")
                    f.write("RESPONSES LOG\n")
                    f.write("=" * 70 + "\n\n")
                    for entry in self.responses_log:
                        f.write(f"[{entry['timestamp'][:19]}] {entry['provider']}\n")
                        f.write(f"Model: {entry.get('model', 'N/A')}\n")
                        f.write(f"Q: {entry['question']}\n")
                        status = "OK" if entry['success'] else "FAIL"
                        f.write(f"Status: {status} | Time: {entry['elapsed_time']:.2f}s\n")
                        f.write(f"Response: {entry['response'][:500]}...\n")
                        f.write("-" * 50 + "\n\n")

                if log_type in ["all", "errors"]:
                    f.write("\n" + "=" * 70 + "\n")
                    f.write("ERRORS LOG\n")
                    f.write("=" * 70 + "\n\n")
                    for entry in self.errors_log:
                        f.write(f"[{entry['timestamp'][:19]}] {entry['provider']}\n")
                        f.write(f"Error: {entry['error']}\n")
                        f.write(f"Code: {entry.get('error_code', 'N/A')}\n")
                        if entry['details']:
                            f.write(f"Details: {entry['details']}\n")
                        f.write("-" * 50 + "\n\n")

                f.write("\n" + "=" * 70 + "\n")
                f.write(f"Total responses: {len(self.responses_log)}\n")
                f.write(f"Total errors: {len(self.errors_log)}\n")
                f.write("=" * 70 + "\n")

            return True
        except Exception as e:
            self.logger.error(f"Failed to export logs: {e}")
            return False

    def clear_logs(self):
        """Clear in-memory logs"""
        self.responses_log.clear()
        self.errors_log.clear()

    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics.clear()
        self._response_times.clear()


# Singleton instance
_logger_instance: Optional[AppLogger] = None


def get_logger(log_dir: str = "logs") -> AppLogger:
    """Get or create logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AppLogger(log_dir)
    return _logger_instance
