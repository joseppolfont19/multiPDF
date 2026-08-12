"""Per-page rotation with a live preview, independent of any toolkit.

The session below holds the pending rotations in memory and only touches disk
on :meth:`PdfRotationSession.save`, which writes to a *new* file: the source
document is never modified in place. In an archive, the master copy is the
one thing you do not overwrite.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image

from ..exceptions import MissingDependencyError

logger = logging.getLogger(__name__)

try:  # PyMuPDF is only needed for rendering and rotation
    import fitz
except ImportError:  # pragma: no cover - exercised only without the extra
    fitz = None


DEFAULT_PREVIEW_ZOOM = 1.5


def _require_pymupdf() -> None:
    if fitz is None:
        raise MissingDependencyError(
            "PyMuPDF no está instalado. Instálalo con: pip install 'archive-pdf-toolkit[gui]'"
        )


class PdfRotationSession:
    """An open PDF plus the rotations queued for each of its pages."""

    def __init__(self, pdf_path: str | Path) -> None:
        _require_pymupdf()
        self.path = Path(pdf_path)
        self.document = fitz.open(str(self.path))
        self.total_pages: int = len(self.document)
        self.page_rotations: list[int] = [0] * self.total_pages
        self.current_page: int = 0
        self._bookmarks = self.document.get_toc(False)
        logger.info(
            "PDF abierto: %s (%d páginas, %d marcadores)",
            self.path.name, self.total_pages, len(self._bookmarks),
        )

    # ---------------- state ----------------

    @property
    def bookmark_count(self) -> int:
        return len(self._bookmarks)

    @property
    def has_pending_rotations(self) -> bool:
        return any(self.page_rotations)

    def rotation_of(self, page_number: int) -> int:
        return self.page_rotations[page_number]

    def is_valid_page(self, page_number: int) -> bool:
        return 0 <= page_number < self.total_pages

    # ---------------- editing ----------------

    def rotate(self, page_number: int, angle: int) -> int:
        """Queue an extra ``angle`` on a page and return its total rotation."""
        if not self.is_valid_page(page_number):
            raise IndexError(f"Página fuera de rango: {page_number}")
        self.page_rotations[page_number] = (self.page_rotations[page_number] + angle) % 360
        return self.page_rotations[page_number]

    def go_to(self, page_number: int) -> int:
        if not self.is_valid_page(page_number):
            raise IndexError(f"Página fuera de rango: {page_number}")
        self.current_page = page_number
        return page_number

    # ---------------- rendering ----------------

    def render_page(self, page_number: int, zoom: float = DEFAULT_PREVIEW_ZOOM) -> Image.Image:
        """Render a page -- with its pending rotation applied -- as an image."""
        if not self.is_valid_page(page_number):
            raise IndexError(f"Página fuera de rango: {page_number}")

        page = self.document[page_number]
        matrix = fitz.Matrix(zoom, zoom)
        pending = self.page_rotations[page_number]
        if pending:
            matrix = matrix.prerotate(pending)

        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return Image.open(io.BytesIO(pixmap.tobytes("ppm")))

    # ---------------- persistence ----------------

    def build_output_path(self) -> Path:
        """Next free ``<name>_rotat[_n].pdf`` beside the source document."""
        base = self.path.with_suffix("")
        candidate = base.with_name(f"{base.name}_rotat.pdf")
        counter = 1
        while candidate.exists():
            candidate = base.with_name(f"{base.name}_rotat_{counter}.pdf")
            counter += 1
        return candidate

    def save(self, output_path: str | Path | None = None) -> Path:
        """Write a rotated copy, preserving the outline, and return its path.

        The source file is reopened rather than reusing the preview document,
        so the saved PDF derives from untouched bytes.
        """
        _require_pymupdf()
        target = Path(output_path) if output_path else self.build_output_path()

        document = fitz.open(str(self.path))
        try:
            for page_number, pending in enumerate(self.page_rotations):
                if not pending:
                    continue
                page = document[page_number]
                page.set_rotation((page.rotation + pending) % 360)
                page.remove_rotation()

            document.save(str(target), deflate=True)
        finally:
            document.close()

        logger.info("PDF rotado guardado en %s", target)
        return target

    # ---------------- lifecycle ----------------

    def close(self) -> None:
        try:
            self.document.close()
        except Exception as exc:  # pragma: no cover
            logger.debug("Error cerrando el documento: %s", exc)

    def __enter__(self) -> PdfRotationSession:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()
