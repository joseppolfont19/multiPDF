"""Turning file names into a navigable PDF outline.

In a digitised archive the file name *is* metadata: it usually carries the
folio or signature. Promoting it to a bookmark is what makes a 900-page PDF
consultable instead of merely storable.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


def count_pages(pdf_path: Path) -> int:
    """Page count, or 0 if the file cannot be read.

    Used by Safe Mode as an integrity probe, so a damaged file must return a
    value rather than raise.
    """
    try:
        return len(PdfReader(str(pdf_path)).pages)
    except Exception as exc:
        logger.warning("No se pudo contar páginas de %s: %s", pdf_path, exc)
        return 0


def add_bookmarks(
    pdf_path: Path,
    image_paths: Sequence[Path],
    root_title: str,
) -> None:
    """Rewrite ``pdf_path`` adding a root bookmark and one entry per page."""
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    parent = writer.add_outline_item(root_title, 0)

    for index, page in enumerate(reader.pages):
        writer.add_page(page)
        if index < len(image_paths):
            writer.add_outline_item(image_paths[index].stem, index, parent)

    with open(pdf_path, "wb") as handle:
        writer.write(handle)

    logger.debug("Marcadores añadidos a %s (%d entradas)", pdf_path.name, len(image_paths))
