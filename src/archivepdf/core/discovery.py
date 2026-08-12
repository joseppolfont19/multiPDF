"""Finding and ordering the images that make up a document.

Page order is not a detail in an archive: a PDF whose pages are sorted
lexicographically ("10" before "2") is a defective reproduction of the
original. Hence the natural sort key below.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from ..config import IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\d+(?:-\d+)*|[^\d]+")
_NUMERIC_RE = re.compile(r"\d+(?:-\d+)*")


def natural_sort_key(name: str) -> list[tuple[int, object]]:
    """Sort key reproducing Windows Explorer ordering.

    Splits a name into numeric and non-numeric tokens so that digits compare
    as numbers, and understands compound folio numbers such as ``12-15``.
    Tokens starting with a hyphen are pushed after their bare counterpart,
    which keeps ``foo`` before ``foo-bis``.

    >>> sorted(["img10.jpg", "img2.jpg"], key=natural_sort_key)
    ['img2.jpg', 'img10.jpg']
    """
    key: list[tuple[int, object]] = []
    for part in _TOKEN_RE.findall(name):
        if _NUMERIC_RE.fullmatch(part):
            key.append((0, tuple(int(x) for x in part.split("-"))))
        elif part.startswith("-"):
            key.append((1, part.lower()))
        else:
            key.append((0, part.lower()))
    return key


def find_images(folder: Path) -> list[Path]:
    """Images directly inside ``folder``, in natural order."""
    return sorted(
        (f for f in folder.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda p: natural_sort_key(p.name),
    )


def find_all_images(folder: Path) -> list[Path]:
    """Every image under ``folder``, recursively (used for global progress)."""
    return [f for f in folder.rglob("*") if f.suffix.lower() in IMAGE_EXTENSIONS]


@dataclass(frozen=True)
class FolderStats:
    """Size summary of a folder tree, used to suggest compression settings."""

    image_count: int
    total_bytes: int

    @property
    def total_mb(self) -> float:
        return self.total_bytes / (1024 * 1024)


def scan_folder(folder: Path) -> FolderStats:
    """Count images and total weight under ``folder``."""
    images = find_all_images(folder)
    total = 0
    for image in images:
        try:
            total += image.stat().st_size
        except OSError:
            logger.warning("No se pudo leer el tamaño de %s", image)
    logger.debug("Escaneo de %s: %d imágenes, %d bytes", folder, len(images), total)
    return FolderStats(image_count=len(images), total_bytes=total)
