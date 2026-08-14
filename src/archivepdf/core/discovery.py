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
    """
    Clau d'ordenació que replica el comportament de Windows Explorer.
    1. Separa números de text de forma estricta.
    2. Prioritza el guió baix '_' sobre el guió '-'.
    3. Tracta els números com a enters per a l'ordenació natural.
    """
    # El "truc": Substituïm temporalment el '_' per un espai o caràcter 
    # que en ASCII vagi ABANS que el '-' (el '-' és el 45, l'espai és el 32).
    # Això força a Windows a posar "SP_" abans que "SP-".
    s_modified = s.lower().replace('_', ' ')
    
    key = []
    # Fem split mantenint els números: 'SP 1881' -> ['SP ', '1881', '']
    for part in re.split(r'(\d+)', s_modified):
        if part.isdigit():
            # (0, valor) indica que és un número (prioritat per davant de text si cal)
            key.append((0, int(part)))
        elif part:
            # (1, text) indica que és text
            key.append((1, part))
            
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
