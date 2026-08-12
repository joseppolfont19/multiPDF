"""Locating bundled assets regardless of how the app was launched."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_path(relative_path: str | Path) -> Path:
    """Absolute path to a bundled asset (icon, logo...).

    Works in three scenarios:
      * frozen with PyInstaller -> the temporary ``_MEIPASS`` folder
      * run from source         -> the folder holding the package, whatever
                                   the current working directory is
      * last resort             -> the current working directory
    """
    try:
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    except Exception:
        try:
            base_path = Path(__file__).resolve().parent
        except Exception:
            base_path = Path(os.path.abspath("."))

    return base_path / relative_path
