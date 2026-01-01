#!/usr/bin/env python3
"""
Structured Logging Configuration
Provides centralized logging with JSON formatting and context
"""

import logging
import json
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

# Get log level from environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "environment": ENVIRONMENT
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Add context fields
        for attr in ["session_id", "tenant_code", "user_id", "correlation_id",
                     "query_id", "processing_time_ms", "sql_query"]:
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)

        return json.dumps(log_data)


class ContextLogger:
    """Logger with context injection capability"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}

    def set_context(self, **kwargs):
        """Set context that will be added to all log messages"""
        self.context.update(kwargs)

    def clear_context(self):
        """Clear all context"""
        self.context = {}

    def _log_with_context(self, level: int, msg: str, **kwargs):
        """Internal method to log with context"""
        extra_data = {**self.context, **kwargs}
        extra = {"extra_data": extra_data}
        self.logger.log(level, msg, extra=extra)

    def debug(self, msg: str, **kwargs):
        self._log_with_context(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self._log_with_context(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._log_with_context(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._log_with_context(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self._log_with_context(logging.CRITICAL, msg, **kwargs)

    def exception(self, msg: str, **kwargs):
        """Log exception with traceback"""
        extra_data = {**self.context, **kwargs}
        extra = {"extra_data": extra_data}
        self.logger.exception(msg, extra=extra)


def setup_logging(log_file: Optional[str] = None) -> None:
    """
    Setup centralized logging configuration

    Args:
        log_file: Optional file path for file logging
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Clear existing handlers
    root_logger.handlers = []

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> ContextLogger:
    """
    Get a context-aware logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        ContextLogger instance
    """
    return ContextLogger(name)


# Initialize logging on module import
setup_logging(log_file="application.log")
