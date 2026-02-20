"""Logging configuration for scrapers."""

import logging
import sys
from pathlib import Path
from typing import Optional

from config.constants import LOG_LEVEL, LOG_FILE


def get_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """Get configured logger instance.

    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        log_level = level or LOG_LEVEL
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Console handler with simple format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # File handler with detailed format
        if log_file or LOG_FILE:
            file_path = log_file or LOG_FILE
            file_handler = logging.FileHandler(file_path, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)

    return logger
