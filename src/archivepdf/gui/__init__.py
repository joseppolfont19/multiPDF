"""Desktop front-end. Importing this package requires the ``gui`` extra."""

from __future__ import annotations

import logging
from pathlib import Path


def launch(log_file: Path | None = None) -> None:
    """Open the application window."""
    from ..logging_setup import configure_logging
    from .app import App

    configure_logging(level=logging.INFO, log_file=log_file)
    App().mainloop()


__all__ = ["launch"]
