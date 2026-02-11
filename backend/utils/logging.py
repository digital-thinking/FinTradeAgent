"""Production logging configuration for FinTradeAgent."""

import sys
import json
import logging
import logging.handlers
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add stack info if present
        if record.stack_info:
            log_entry["stack_info"] = self.formatStack(record.stack_info)
        
        # Add extra fields from record
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info', 'message'
                }:
                    try:
                        # Only include serializable values
                        json.dumps(value)
                        log_entry[key] = value
                    except (TypeError, ValueError):
                        log_entry[key] = str(value)
        
        return json.dumps(log_entry, ensure_ascii=False)


class ProductionLogFilter(logging.Filter):
    """Filter for production logging to exclude sensitive information."""
    
    SENSITIVE_KEYS = {
        'password', 'token', 'key', 'secret', 'authorization',
        'cookie', 'session', 'api_key', 'access_token', 'refresh_token'
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive information from log records."""
        
        # Sanitize message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._sanitize_text(record.msg)
        
        # Sanitize extra fields
        for key, value in list(record.__dict__.items()):
            if key.lower() in self.SENSITIVE_KEYS:
                record.__dict__[key] = "[REDACTED]"
            elif isinstance(value, str):
                record.__dict__[key] = self._sanitize_text(value)
            elif isinstance(value, dict):
                record.__dict__[key] = self._sanitize_dict(value)
        
        return True
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize sensitive information from text."""
        import re
        
        # Common patterns for sensitive data
        patterns = [
            (r'password["\s]*[:=]["\s]*[^"\s]+', 'password="[REDACTED]"'),
            (r'token["\s]*[:=]["\s]*[^"\s]+', 'token="[REDACTED]"'),
            (r'key["\s]*[:=]["\s]*[^"\s]+', 'key="[REDACTED]"'),
            (r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', 'Bearer [REDACTED]'),
            (r'Basic\s+[A-Za-z0-9+/=]+', 'Basic [REDACTED]'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _sanitize_dict(self, data: dict) -> dict:
        """Sanitize sensitive information from dictionary."""
        sanitized = {}
        for key, value in data.items():
            if key.lower() in self.SENSITIVE_KEYS:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            else:
                sanitized[key] = value
        return sanitized


def setup_production_logging(settings) -> None:
    """Setup production logging configuration."""
    
    # Create logs directory if it doesn't exist
    log_file_path = Path(settings.log_file)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # JSON formatter for structured logging
    json_formatter = JSONFormatter(include_extra=True)
    
    # Console handler for development/debugging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    if settings.log_format.lower() == 'json':
        console_handler.setFormatter(json_formatter)
    else:
        # Human-readable format for console
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
    
    # Add production log filter
    production_filter = ProductionLogFilter()
    console_handler.addFilter(production_filter)
    
    root_logger.addHandler(console_handler)
    
    # File handler for persistent logging
    try:
        # Parse log file size
        max_bytes = _parse_size(settings.log_max_size)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.log_file,
            maxBytes=max_bytes,
            backupCount=settings.log_backup_count,
            encoding='utf-8'
        )
        
        file_handler.setLevel(getattr(logging, settings.log_level.upper()))
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(production_filter)
        
        root_logger.addHandler(file_handler)
        
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")
    
    # Error file handler for errors only
    try:
        error_log_path = log_file_path.parent / f"error_{log_file_path.name}"
        error_handler = logging.handlers.RotatingFileHandler(
            filename=error_log_path,
            maxBytes=max_bytes,
            backupCount=settings.log_backup_count,
            encoding='utf-8'
        )
        
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        error_handler.addFilter(production_filter)
        
        root_logger.addHandler(error_handler)
        
    except Exception as e:
        print(f"Warning: Could not setup error file logging: {e}")
    
    # Configure specific loggers
    _configure_specific_loggers(settings)
    
    # Setup Sentry integration if configured
    if settings.sentry_dsn:
        _setup_sentry_logging(settings.sentry_dsn, settings.app_env)
    
    # Log successful configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Production logging configured",
        extra={
            "log_level": settings.log_level,
            "log_format": settings.log_format,
            "log_file": settings.log_file,
            "sentry_enabled": bool(settings.sentry_dsn)
        }
    )


def _configure_specific_loggers(settings) -> None:
    """Configure logging levels for specific modules."""
    
    # Reduce noise from third-party libraries
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Application-specific loggers
    logging.getLogger('backend').setLevel(getattr(logging, settings.log_level.upper()))
    logging.getLogger('fin_trade').setLevel(getattr(logging, settings.log_level.upper()))


def _setup_sentry_logging(sentry_dsn: str, environment: str) -> None:
    """Setup Sentry error tracking integration."""
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        
        # Configure Sentry integrations
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            integrations=[sentry_logging, FastApiIntegration()],
            # Performance monitoring
            traces_sample_rate=0.1,  # 10% of requests
            # Release tracking
            release="fintradeagent@1.0.0",
            # Additional options
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send personally identifiable info
            max_breadcrumbs=50,
            # Custom before_send hook to filter sensitive data
            before_send=_sentry_before_send,
        )
        
        logging.getLogger(__name__).info("Sentry error tracking initialized")
        
    except ImportError:
        logging.getLogger(__name__).warning(
            "Sentry SDK not installed, error tracking disabled"
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to initialize Sentry: {e}")


def _sentry_before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter sensitive data before sending to Sentry."""
    
    # Remove sensitive data from event
    if 'request' in event:
        request_data = event['request']
        
        # Remove sensitive headers
        if 'headers' in request_data:
            headers = request_data['headers']
            for key in list(headers.keys()):
                if key.lower() in {'authorization', 'cookie', 'x-api-key'}:
                    headers[key] = '[Filtered]'
        
        # Remove sensitive query parameters
        if 'query_string' in request_data:
            # Filter sensitive query parameters
            query_string = request_data['query_string']
            if any(sensitive in query_string.lower() for sensitive in ['password', 'token', 'key']):
                request_data['query_string'] = '[Filtered]'
        
        # Remove sensitive data from request body
        if 'data' in request_data:
            # Don't log request bodies to avoid sensitive data
            request_data['data'] = '[Filtered]'
    
    return event


def _parse_size(size_str: str) -> int:
    """Parse size string like '100MB' to bytes."""
    size_str = size_str.upper()
    
    if size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('B'):
        return int(size_str[:-1])
    else:
        # Assume bytes if no suffix
        return int(size_str)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with production configuration."""
    return logging.getLogger(name)