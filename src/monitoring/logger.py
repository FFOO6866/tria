"""
Structured Logging Module
==========================

Production-grade logging with structured data, levels, and context.

Features:
1. Structured logging (JSON format)
2. Multiple log levels
3. Context enrichment
4. Performance logging
5. Error tracking with stack traces
6. Request/response logging

NO MOCKING - Real production logging
"""

import logging
import json
import time
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import sys

# Create logs directory
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class StructuredLogger:
    """
    Structured logger for production monitoring

    Logs in JSON format with context enrichment.
    """

    def __init__(self, name: str, log_file: Optional[str] = None):
        """
        Initialize structured logger

        Args:
            name: Logger name (usually module name)
            log_file: Optional log file path
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers
        self.logger.handlers = []

        # Console handler (for development)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self._get_formatter())
        self.logger.addHandler(console_handler)

        # File handler (for production)
        if log_file:
            file_handler = logging.FileHandler(LOG_DIR / log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(self._get_formatter())
            self.logger.addHandler(file_handler)

    def _get_formatter(self) -> logging.Formatter:
        """Get JSON formatter"""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _build_log_entry(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> Dict[str, Any]:
        """Build structured log entry"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "logger": self.logger.name
        }

        # Add context
        if context:
            entry["context"] = context

        # Add error details
        if error:
            entry["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            }

        return entry

    def info(self, message: str, **context):
        """Log info message"""
        entry = self._build_log_entry("INFO", message, context)
        self.logger.info(json.dumps(entry))

    def warning(self, message: str, **context):
        """Log warning message"""
        entry = self._build_log_entry("WARNING", message, context)
        self.logger.warning(json.dumps(entry))

    def error(self, message: str, error: Optional[Exception] = None, **context):
        """Log error message"""
        entry = self._build_log_entry("ERROR", message, context, error)
        self.logger.error(json.dumps(entry))

    def critical(self, message: str, error: Optional[Exception] = None, **context):
        """Log critical message"""
        entry = self._build_log_entry("CRITICAL", message, context, error)
        self.logger.critical(json.dumps(entry))

    def debug(self, message: str, **context):
        """Log debug message"""
        entry = self._build_log_entry("DEBUG", message, context)
        self.logger.debug(json.dumps(entry))


class RequestLogger:
    """Logger for HTTP requests and API calls"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def log_request(
        self,
        method: str,
        endpoint: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        **context
    ):
        """Log incoming request"""
        self.logger.info(
            f"Request: {method} {endpoint}",
            method=method,
            endpoint=endpoint,
            user_id=user_id,
            ip_address=ip_address,
            **context
        )

    def log_response(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        latency_ms: float,
        user_id: Optional[str] = None,
        **context
    ):
        """Log response"""
        level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"

        log_method = getattr(self.logger, level)
        log_method(
            f"Response: {method} {endpoint} - {status_code} ({latency_ms:.0f}ms)",
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            latency_ms=latency_ms,
            user_id=user_id,
            **context
        )


class PerformanceLogger:
    """Logger for performance metrics"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.start_time = None

    def __enter__(self):
        """Start timing"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log performance"""
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.logger.info(
                f"Performance: {duration_ms:.0f}ms",
                duration_ms=duration_ms
            )

    def log_operation(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **context
    ):
        """Log operation performance"""
        self.logger.info(
            f"Operation: {operation} - {duration_ms:.0f}ms",
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            **context
        )


class ErrorTracker:
    """Track and log errors with context"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.error_counts = {}

    def track_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: str = "error"
    ):
        """
        Track error occurrence

        Args:
            error: Exception that occurred
            context: Additional context about the error
            severity: Error severity (error, critical, warning)
        """
        error_type = type(error).__name__

        # Count errors
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # Log error
        log_method = getattr(self.logger, severity)
        log_method(
            f"Error: {error_type} - {str(error)}",
            error=error,
            error_count=self.error_counts[error_type],
            **(context or {})
        )

    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of error counts"""
        return self.error_counts.copy()


# Global loggers
app_logger = StructuredLogger("tria.app", "app.log")
request_logger = RequestLogger(app_logger)
performance_logger = PerformanceLogger(app_logger)
error_tracker = ErrorTracker(app_logger)


# Convenience functions
def log_info(message: str, **context):
    """Log info message"""
    app_logger.info(message, **context)


def log_warning(message: str, **context):
    """Log warning message"""
    app_logger.warning(message, **context)


def log_error(message: str, error: Optional[Exception] = None, **context):
    """Log error message"""
    app_logger.error(message, error=error, **context)


def log_critical(message: str, error: Optional[Exception] = None, **context):
    """Log critical message"""
    app_logger.critical(message, error=error, **context)


def log_request(method: str, endpoint: str, **context):
    """Log HTTP request"""
    request_logger.log_request(method, endpoint, **context)


def log_response(method: str, endpoint: str, status_code: int, latency_ms: float, **context):
    """Log HTTP response"""
    request_logger.log_response(method, endpoint, status_code, latency_ms, **context)


def track_error(error: Exception, **context):
    """Track error occurrence"""
    error_tracker.track_error(error, context)
