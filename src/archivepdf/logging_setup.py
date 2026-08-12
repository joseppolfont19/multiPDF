"""Logging setup.

The core emits log records; it never opens dialogs. Callers choose the
destination: stderr for the CLI, a rotating file for the GUI, nothing at all
for tests.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
) -> logging.Logger:
    """Configure the package logger and return it."""
    logger = logging.getLogger("archivepdf")
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger
