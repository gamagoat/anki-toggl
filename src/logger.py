import logging
import sys
from datetime import datetime
from pathlib import Path

from .constants import (
    LOG_DATE_FORMAT,
    LOG_FILE_PREFIX,
    LOG_MESSAGE_FORMAT,
    LOG_TIMESTAMP_FORMAT,
)

_logger_configured = False


def get_module_logger(module_name: str = "anki_toggl") -> logging.Logger:
    """Return a named logger; handlers are managed on the root logger."""
    setup_logger()
    return logging.getLogger(module_name)


def setup_logger() -> logging.Logger:
    global _logger_configured

    logger = logging.getLogger()

    if _logger_configured:
        return logger

    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        LOG_MESSAGE_FORMAT,
        datefmt=LOG_TIMESTAMP_FORMAT,
    )

    console_handler = logging.StreamHandler(sys.stdout)
    level = logging.DEBUG
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime(LOG_DATE_FORMAT)
        log_file = logs_dir / f"{LOG_FILE_PREFIX}{timestamp}.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to: {log_file}")

    except Exception as e:
        logger.warning(f"Could not set up file logging: {e}")

    _logger_configured = True
    return logger
