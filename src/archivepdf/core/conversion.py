"""The conversion pipeline: images in, verified PDF out.

Design notes
------------
*Chunking*: images are processed in fixed-size groups, each written to its own
temporary PDF and merged at the end. Peak memory therefore depends on the
chunk size, not on the size of the job. A 20.000-image run uses the same RAM
as a 200-image one.

*Safe Mode*: past ``SAFE_MODE_THRESHOLD`` images, every chunk is verified page
by page; a chunk that comes out short is regenerated once, and only then does
the job fail. The final PDF is verified too. Silent page loss in an archival
reproduction is worse than a crash.

*Idempotency*: an existing output is never rebuilt, so an interrupted run can
simply be relaunched.

This module replaces four near-identical functions of the original monolith
(``convertir_a_pdf``, ``convertir_a_pdf_comprimit``, ``processar_carpeta`` and
``processar_carpeta_comprimida``) with one pipeline parameterised by
:class:`~archivepdf.config.ConversionConfig`.
"""

from __future__ import annotations

import gc
import io
import logging
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path

from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter

from ..config import MAX_TREE_DEPTH, RECTO_DIR, SAFE_MODE_THRESHOLD, VERSO_DIR, ConversionConfig
from ..exceptions import IntegrityError, UnreadableImageError
from .bookmarks import add_bookmarks, count_pages
from .discovery import find_images, natural_sort_key
from .resources import wait_for_resources

logger = logging.getLogger(__name__)

# (processed_images, total_images)
ProgressCallback = Callable[[int, int], None]


# --------------------------------------------------------------------------
# Image loading
# --------------------------------------------------------------------------

def open_and_transform(image_path: Path, scale_percent: int = 100) -> Image.Image:
    """Open an image, honour its EXIF orientation, convert to RGB and scale.

    EXIF transposition matters: scanners and cameras routinely store a
    landscape sensor image plus a "rotate me" flag. Ignoring it produces a PDF
    where half the folios lie on their side.
    """
    try:
        image = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
    except Exception as exc:
        raise UnreadableImageError(image_path, exc) from exc

    if scale_percent != 100:
        width, height = image.size
        new_size = (
            max(1, int(width * scale_percent / 100)),
            max(1, int(height * scale_percent / 100)),
        )
        image = image.resize(new_size, Image.LANCZOS)

    return image


# --------------------------------------------------------------------------
# Chunk generation and merging
# --------------------------------------------------------------------------

def _write_chunk(
    chunk: Sequence[Path],
    chunk_pdf: Path,
    config: ConversionConfig,
    chunk_index: int,
    chunk_size: int,
    total: int,
    progress_callback: ProgressCallback | None,
    report_progress: bool,
) -> None:
    """Render one group of images into a single temporary PDF."""
    frames: list[Image.Image] = []
    try:
        for image_path in chunk:
            frames.append(open_and_transform(image_path, config.scale_percent))
            if report_progress and progress_callback is not None:
                progress_callback(chunk_index * chunk_size + len(frames), total)

        save_kwargs: dict[str, object] = {
            "save_all": True,
            "append_images": frames[1:],
            "quality": config.quality,
            "optimize": True,
        }
        if config.dpi:
            save_kwargs["dpi"] = (config.dpi, config.dpi)

        frames[0].save(chunk_pdf, **save_kwargs)
    finally:
        for frame in frames:
            frame.close()
        frames.clear()
        gc.collect()


def _merge_chunks(chunk_paths: Sequence[Path], output_path: Path) -> None:
    """Concatenate the temporary chunk PDFs into the final document.

    Each chunk is read into memory and its reader kept alive until the write
    completes: pypdf resolves page content lazily, so releasing a reader too
    early yields a structurally valid PDF with empty pages.
    """
    writer = PdfWriter()
    readers: list[PdfReader] = []
    buffers: list[io.BytesIO] = []

    try:
        for chunk_pdf in chunk_paths:
            with open(chunk_pdf, "rb") as handle:
                buffer = io.BytesIO(handle.read())
            reader = PdfReader(buffer)
            for page in reader.pages:
                writer.add_page(page)
            readers.append(reader)
            buffers.append(buffer)

        with open(output_path, "wb") as handle:
            writer.write(handle)
    finally:
        readers.clear()
        buffers.clear()
        del writer
        gc.collect()


def images_to_pdf(
    images: Sequence[Path],
    output_path: Path,
    config: ConversionConfig,
    progress_callback: ProgressCallback | None = None,
) -> bool:
    """Convert ``images`` into a single PDF at ``output_path``.

    Returns ``False`` when there is nothing to do, ``True`` on success.
    Raises :class:`UnreadableImageError` or :class:`IntegrityError` on failure.
    """
    if not images:
        return False

    total = len(images)
    safe_mode = total > SAFE_MODE_THRESHOLD
    chunk_size = config.resolve_chunk_size(total)
    temp_dir = output_path.parent / f"_tmp_{output_path.stem}"
    temp_dir.mkdir(exist_ok=True)

    logger.info(
        "Generando %s | %d imágenes | chunk=%d | safe_mode=%s | calidad=%d | dpi=%s | escala=%d%%",
        output_path.name, total, chunk_size, safe_mode,
        config.quality, config.dpi or "-", config.scale_percent,
    )

    try:
        chunks = [images[i:i + chunk_size] for i in range(0, total, chunk_size)]
        chunk_paths: list[Path] = []

        for chunk_index, chunk in enumerate(chunks):
            if config.throttle_resources:
                wait_for_resources()

            chunk_pdf = temp_dir / f"chunk_{chunk_index:04d}.pdf"
            _write_chunk(
                chunk, chunk_pdf, config, chunk_index, chunk_size,
                total, progress_callback, report_progress=True,
            )

            if safe_mode:
                _verify_chunk(
                    chunk, chunk_pdf, config, chunk_index, chunk_size,
                    total, progress_callback,
                )

            chunk_paths.append(chunk_pdf)

        _merge_chunks(chunk_paths, output_path)

        if safe_mode:
            final_pages = count_pages(output_path)
            if final_pages != total:
                output_path.unlink(missing_ok=True)
                raise IntegrityError(
                    f"El PDF final tiene {final_pages} páginas y se esperaban {total}."
                )

        logger.info("PDF generado correctamente: %s (%d páginas)", output_path.name, total)
        return True

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def _verify_chunk(
    chunk: Sequence[Path],
    chunk_pdf: Path,
    config: ConversionConfig,
    chunk_index: int,
    chunk_size: int,
    total: int,
    progress_callback: ProgressCallback | None,
) -> None:
    """Safe Mode: check the chunk's page count, regenerate once, then fail."""
    if count_pages(chunk_pdf) == len(chunk):
        return

    logger.warning("Chunk %d defectuoso, se regenera una vez", chunk_index)
    chunk_pdf.unlink(missing_ok=True)

    if config.throttle_resources:
        wait_for_resources()

    _write_chunk(
        chunk, chunk_pdf, config, chunk_index, chunk_size,
        total, progress_callback, report_progress=False,
    )

    if count_pages(chunk_pdf) != len(chunk):
        raise IntegrityError(f"Chunk {chunk_index} defectuoso después de reintentarlo.")


# --------------------------------------------------------------------------
# Folder tree traversal
# --------------------------------------------------------------------------

def build_pdf_for_folder(
    folder: Path,
    images: Sequence[Path],
    config: ConversionConfig,
    errors: list[str],
    progress_callback: ProgressCallback | None = None,
) -> bool:
    """Build (and bookmark) the PDF for one folder, recording any failure.

    Existing output is left untouched, which makes the whole run resumable.
    """
    output_path = folder / config.output_name(folder.name)

    if output_path.exists():
        logger.debug("Ya existe, se omite: %s", output_path.name)
        return True

    try:
        if images_to_pdf(images, output_path, config, progress_callback):
            add_bookmarks(output_path, images, folder.name)
        return True
    except Exception as exc:
        logger.error("Fallo procesando %s: %s", folder.name, exc)
        errors.append(f"{folder.name} (Error: {exc})")
        return False


def _combine_recto_verso(
    base_dir: Path,
    config: ConversionConfig,
    errors: list[str],
    progress_callback: ProgressCallback | None = None,
) -> bool:
    """Merge the ``R`` and ``V`` sub-folders of a document into one PDF.

    Bound documents are digitised in two passes -- all rectos, then all versos.
    Interleaving them back by natural name order reconstructs the reading order
    of the original.
    """
    recto = base_dir / RECTO_DIR
    verso = base_dir / VERSO_DIR

    if not (recto.exists() and verso.exists()):
        return False

    images = sorted(
        find_images(recto) + find_images(verso),
        key=lambda p: natural_sort_key(p.name),
    )
    return build_pdf_for_folder(base_dir, images, config, errors, progress_callback)


def process_tree(
    base_dir: Path,
    config: ConversionConfig,
    errors: list[str],
    progress_callback: ProgressCallback | None = None,
    level: int = 0,
    max_level: int = MAX_TREE_DEPTH,
) -> None:
    """Walk a folder tree, generating one PDF per document folder.

    A folder holding both ``R`` and ``V`` is treated as a single document; any
    other folder holding images becomes a PDF of its own. Recursion is capped
    to avoid pathological trees.
    """
    if level > max_level:
        logger.warning("Profundidad máxima alcanzada en %s", base_dir)
        return

    subfolders = [f for f in base_dir.iterdir() if f.is_dir()]
    subfolder_names = {f.name.upper() for f in subfolders}

    if RECTO_DIR in subfolder_names and VERSO_DIR in subfolder_names:
        _combine_recto_verso(base_dir, config, errors, progress_callback)
        for folder in subfolders:
            if folder.name.upper() not in {RECTO_DIR, VERSO_DIR}:
                process_tree(folder, config, errors, progress_callback, level + 1, max_level)
        return

    images = find_images(base_dir)
    if images:
        build_pdf_for_folder(base_dir, images, config, errors, progress_callback)

    for folder in subfolders:
        process_tree(folder, config, errors, progress_callback, level + 1, max_level)
