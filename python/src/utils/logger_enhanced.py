"""Enhanced logging configuration for scrapers with structured logging support."""

import logging
import sys
import json
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime
from contextlib import contextmanager

from config.constants import LOG_LEVEL, LOG_FILE, BASE_DIR


# Custom log levels for special events
logging.MAINTENANCE = 25  # Between WARNING and INFO
logging.addLevelName(logging.MAINTENANCE, "MAINTENANCE")

# Color codes for console output
LOG_COLORS = {
    'DEBUG': '\033[36m',      # Cyan
    'INFO': '\033[32m',       # Green
    'MAINTENANCE': '\033[33m', # Yellow
    'WARNING': '\033[33m',    # Yellow
    'ERROR': '\033[31m',      # Red
    'CRITICAL': '\033[35m',   # Magenta
    'RESET': '\033[0m'
}


class ColoredFormatter(logging.Formatter):
    """Console formatter with colors for better readability."""

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

    def format(self, record):
        if self.use_colors:
            level_color = LOG_COLORS.get(record.levelname, '')
            record.levelname = f"{level_color}{record.levelname}{LOG_COLORS['RESET']}"

        # Add scraper name if available
        if hasattr(record, 'scraper'):
            record.scraper_name = record.scraper
        else:
            record.scraper_name = record.name.split('.')[-1]

        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging to files."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add extra fields from record
        if hasattr(record, 'scraper'):
            log_entry['scraper'] = record.scraper
        if hasattr(record, 'ico'):
            log_entry['ico'] = record.ico
        if hasattr(record, 'url'):
            log_entry['url'] = record.url
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)

        # Exception info
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class ScraperLogger:
    """Enhanced logger wrapper for scrapers with structured logging."""

    def __init__(
        self,
        name: str,
        level: Optional[str] = None,
        log_file: Optional[Path] = None,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_colors: bool = True
    ):
        """Initialize scraper logger.

        Args:
            name: Logger name (typically __name__ or scraper class name)
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file path
            enable_console: Enable console output
            enable_file: Enable file output
            enable_colors: Enable colored console output
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.log_file = log_file or LOG_FILE

        # Only configure if not already configured
        if not self.logger.handlers:
            self._setup_logger(level, enable_console, enable_file, enable_colors)

    def _setup_logger(self, level: Optional[str], enable_console: bool, enable_file: bool, enable_colors: bool):
        """Setup logger with handlers."""
        log_level = getattr(logging, (level or LOG_LEVEL).upper(), logging.INFO)
        self.logger.setLevel(logging.DEBUG)  # Capture all levels, handlers filter

        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_format = ColoredFormatter.get_default_format() if not enable_colors else ColoredFormatter(
                '%(scraper_name)s | %(levelname)-8s | %(message)s',
                use_colors=True
            )
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)

        # File handler with JSON structured logging
        if enable_file and self.log_file:
            # Ensure log directory exists
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(StructuredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(file_handler)

    # Convenience methods with context
    def debug(self, msg: str, **kwargs):
        """Log debug message."""
        extra = kwargs.pop('extra', {})
        self._log(logging.DEBUG, msg, extra=extra)

    def info(self, msg: str, **kwargs):
        """Log info message."""
        extra = kwargs.pop('extra', {})
        self._log(logging.INFO, msg, extra=extra)

    def warning(self, msg: str, **kwargs):
        """Log warning message."""
        extra = kwargs.pop('extra', {})
        self._log(logging.WARNING, msg, extra=extra)

    def error(self, msg: str, **kwargs):
        """Log error message."""
        extra = kwargs.pop('extra', {})
        self._log(logging.ERROR, msg, extra=extra)

    def critical(self, msg: str, **kwargs):
        """Log critical message."""
        extra = kwargs.pop('extra', {})
        self._log(logging.CRITICAL, msg, extra=extra)

    def maintenance(self, msg: str, **kwargs):
        """Log maintenance message."""
        extra = kwargs.pop('extra', {})
        self._log(logging.MAINTENANCE, msg, extra=extra)

    def _log(self, level: int, msg: str, extra: Optional[Dict] = None):
        """Internal log method with extra context."""
        if extra:
            self.logger.log(level, msg, extra={'extra': extra})
        else:
            self.logger.log(level, msg)

    # Context-specific logging methods
    def log_request(self, method: str, url: str, **kwargs):
        """Log HTTP request."""
        self.info(f"{method} {url}", extra={'url': url, 'action': 'request', **kwargs})

    def log_response(self, url: str, status_code: int, duration_ms: float, **kwargs):
        """Log HTTP response."""
        level = logging.WARNING if status_code >= 400 else logging.DEBUG
        self.logger.log(
            level,
            f"{status_code} from {url} ({duration_ms:.0f}ms)",
            extra={'url': url, 'status_code': status_code, 'duration_ms': duration_ms, 'action': 'response'}
        )

    def log_parse_start(self, data_source: str, **kwargs):
        """Log parse start."""
        self.debug(f"Parsing data from {data_source}", extra={'action': 'parse_start', 'source': data_source})

    def log_parse_complete(self, data_source: str, items_found: int = 0, **kwargs):
        """Log parse complete."""
        self.info(
            f"Parsed {data_source}: {items_found} items",
            extra={'action': 'parse_complete', 'source': data_source, 'items_found': items_found}
        )

    def log_maintenance(self, source: str, **kwargs):
        """Log maintenance detected."""
        self.maintenance(
            f"{source} is under maintenance",
            extra={'action': 'maintenance', 'source': source}
        )

    def log_rate_limit(self, delay: float, **kwargs):
        """Log rate limit delay."""
        self.debug(f"Rate limit: waiting {delay:.1f}s", extra={'action': 'rate_limit', 'delay': delay})

    def log_mock_fallback(self, source: str, reason: str, **kwargs):
        """Log mock data fallback."""
        self.warning(
            f"Using mock data for {source}: {reason}",
            extra={'action': 'mock_fallback', 'source': source, 'reason': reason}
        )

    @contextmanager
    def log_context(self, operation: str, **context):
        """Context manager for logging operation start/end."""
        self.debug(f"{operation} started", extra={'action': operation, **context})
        try:
            yield
        finally:
            self.debug(f"{operation} completed", extra={'action': operation, **context})

    def get_logger(self) -> logging.Logger:
        """Get the underlying logger instance."""
        return self.logger


def get_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    use_enhanced: bool = True
) -> logging.Logger:
    """Get configured logger instance (backward compatible).

    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        use_enhanced: Use enhanced ScraperLogger

    Returns:
        Configured logger instance
    """
    if use_enhanced:
        scraper_logger = ScraperLogger(name, level=level, log_file=log_file)
        return scraper_logger.get_logger()
    else:
        # Original simple logger for backward compatibility
        logger = logging.getLogger(name)

        if not logger.handlers:
            log_level = level or LOG_LEVEL
            logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_format = logging.Formatter('%(levelname)s - %(message)s')
            console_handler.setFormatter(console_format)
            logger.addHandler(console_handler)

            if log_file or LOG_FILE:
                file_path = log_file or LOG_FILE
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(file_path, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                file_format = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_format)
                logger.addHandler(file_handler)

        return logger
