"""Command line interface.

The GUI is convenient; the CLI is what makes the tool automatable. Same core,
no dialogs, exit codes a scheduler can read, and an optional CSV manifest of
the run that can be loaded straight into pandas or Power BI.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import DPI_OPTIONS, QUALITY_PRESETS, SCALE_OPTIONS, ConversionConfig
from .core.compression import format_size, recommend_settings
from .core.conversion import process_tree
from .core.discovery import find_all_images, scan_folder
from .logging_setup import configure_logging

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_FAILED = 2


# --------------------------------------------------------------------------
# Run manifest
# --------------------------------------------------------------------------

@dataclass
class RunRecord:
    """One row of the run manifest -- the raw material for later analysis."""

    root: str
    profile: str
    images: int
    source_mb: float
    output_mb: float
    pdfs_created: int
    errors: int
    duration_seconds: float

    @property
    def compression_ratio(self) -> float | None:
        if not self.source_mb:
            return None
        return round(self.output_mb / self.source_mb, 4)


def write_manifest(path: Path, record: RunRecord) -> None:
    """Append the run to a CSV manifest, writing the header if new."""
    row = asdict(record) | {"compression_ratio": record.compression_ratio}
    is_new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        if is_new:
            writer.writeheader()
        writer.writerow(row)

    logger.info("Manifiesto actualizado: %s", path)


def _pdf_size_mb(root: Path, suffix: str) -> tuple[int, float]:
    pattern = f"*{suffix}.pdf" if suffix else "*.pdf"
    pdfs = [p for p in root.rglob(pattern) if p.is_file()]
    total = sum(p.stat().st_size for p in pdfs)
    return len(pdfs), total / (1024 * 1024)


# --------------------------------------------------------------------------
# Progress reporting
# --------------------------------------------------------------------------

class ConsoleProgress:
    """Minimal single-line progress meter driven by the pipeline callback."""

    def __init__(self, total: int, quiet: bool = False) -> None:
        self.total = max(total, 1)
        self.done = 0
        self.quiet = quiet

    def __call__(self, _current: int, _folder_total: int) -> None:
        self.done += 1
        if self.quiet:
            return
        percent = min(self.done / self.total, 1.0) * 100
        sys.stderr.write(f"\r  {self.done}/{self.total} imágenes  ({percent:5.1f}%)")
        sys.stderr.flush()

    def finish(self) -> None:
        if not self.quiet:
            sys.stderr.write("\n")
            sys.stderr.flush()


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_scan(args: argparse.Namespace) -> int:
    """Report size and suggest compression settings without writing anything."""
    root: Path = args.folder
    stats = scan_folder(root)

    if stats.image_count == 0:
        print(f"No se han encontrado imágenes en {root}")
        return EXIT_FAILED

    recommendation = recommend_settings(stats.total_mb, stats.image_count)
    print(f"Carpeta      : {root}")
    print(f"Imágenes     : {stats.image_count}")
    print(f"Peso total   : {format_size(stats.total_mb)}")
    print("Recomendación:")
    for line in recommendation.info.splitlines()[1:]:
        print(f"  {line}")
    print(
        f"  → --dpi {recommendation.dpi} "
        f"--quality {QUALITY_PRESETS[recommendation.quality]} "
        f"--scale {recommendation.scale.rstrip('%')}"
    )
    return EXIT_OK


def _run_conversion(args: argparse.Namespace, config: ConversionConfig, profile: str) -> int:
    root: Path = args.folder
    images = find_all_images(root)

    if not images:
        print(f"No se han encontrado imágenes en {root}", file=sys.stderr)
        return EXIT_FAILED

    source_mb = sum(i.stat().st_size for i in images) / (1024 * 1024)
    progress = ConsoleProgress(len(images), quiet=args.quiet)
    errors: list[str] = []
    started = time.monotonic()

    process_tree(root, config, errors, progress_callback=progress)

    progress.finish()
    duration = time.monotonic() - started
    pdf_count, output_mb = _pdf_size_mb(root, config.output_suffix)

    record = RunRecord(
        root=str(root),
        profile=profile,
        images=len(images),
        source_mb=round(source_mb, 2),
        output_mb=round(output_mb, 2),
        pdfs_created=pdf_count,
        errors=len(errors),
        duration_seconds=round(duration, 2),
    )

    print(
        f"\n{pdf_count} PDF(s) · {len(images)} imágenes · "
        f"{format_size(source_mb)} → {format_size(output_mb)} · {duration:.1f}s"
    )

    if errors:
        print(f"\n{len(errors)} carpeta(s) con errores:", file=sys.stderr)
        for entry in errors:
            print(f"  - {entry}", file=sys.stderr)

    if args.report:
        write_manifest(args.report, record)

    return EXIT_PARTIAL if errors else EXIT_OK


def cmd_convert(args: argparse.Namespace) -> int:
    """Standard conversion (the "Convertidor" profile)."""
    config = ConversionConfig.standard(halve_resolution=args.half_resolution)
    return _run_conversion(args, config, profile="standard")


def cmd_compress(args: argparse.Namespace) -> int:
    """Compressed conversion (the "Optimitzador" profile)."""
    if args.auto:
        stats = scan_folder(args.folder)
        recommendation = recommend_settings(stats.total_mb, stats.image_count)
        dpi = int(recommendation.dpi)
        quality = QUALITY_PRESETS[recommendation.quality]
        scale = int(recommendation.scale.rstrip("%"))
        logger.info("Ajustes automáticos: dpi=%d quality=%d scale=%d%%", dpi, quality, scale)
    else:
        dpi, quality, scale = args.dpi, args.quality, args.scale

    config = ConversionConfig.compressed(dpi=dpi, quality=quality, scale_percent=scale)
    return _run_conversion(args, config, profile="compressed")


def cmd_rotate(args: argparse.Namespace) -> int:
    """Apply a fixed rotation to selected pages of an existing PDF."""
    from .core.rotation import PdfRotationSession  # imported lazily: needs PyMuPDF

    session = PdfRotationSession(args.pdf)
    try:
        if args.pages:
            targets = [p - 1 for p in args.pages]
        else:
            targets = list(range(session.total_pages))

        for page_number in targets:
            if not session.is_valid_page(page_number):
                print(f"Página fuera de rango: {page_number + 1}", file=sys.stderr)
                return EXIT_FAILED
            session.rotate(page_number, args.angle)

        output = session.save(args.output)
    finally:
        session.close()

    print(f"Guardado: {output}")
    return EXIT_OK


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="archivepdf",
        description="Conversión por lotes de imágenes digitalizadas a PDF verificado.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="registro detallado")
    parser.add_argument("-q", "--quiet", action="store_true", help="sin barra de progreso")
    parser.add_argument("--log-file", type=Path, help="además del stderr, escribe el log aquí")

    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("folder", type=Path, help="carpeta raíz a procesar")
        sub.add_argument("--report", type=Path, help="CSV donde registrar la ejecución")

    scan = subparsers.add_parser("scan", help="analiza una carpeta y recomienda ajustes")
    scan.add_argument("folder", type=Path)
    scan.set_defaults(func=cmd_scan)

    convert = subparsers.add_parser("convert", help="conversión estándar a PDF")
    add_common(convert)
    convert.add_argument(
        "--half-resolution", action="store_true",
        help="reduce las imágenes al 50 %% (perfil 'Usuari')",
    )
    convert.set_defaults(func=cmd_convert)

    compress = subparsers.add_parser("compress", help="conversión a PDF comprimido")
    add_common(compress)
    compress.add_argument("--dpi", type=int, default=150, choices=[int(d) for d in DPI_OPTIONS])
    compress.add_argument("--quality", type=int, default=65, help="calidad JPEG (1-95)")
    compress.add_argument(
        "--scale", type=int, default=100,
        choices=[int(s.rstrip("%")) for s in SCALE_OPTIONS],
        help="escala de la imagen en %%",
    )
    compress.add_argument(
        "--auto", action="store_true",
        help="ignora los valores anteriores y aplica la recomendación automática",
    )
    compress.set_defaults(func=cmd_compress)

    rotate = subparsers.add_parser("rotate", help="rota páginas de un PDF existente")
    rotate.add_argument("pdf", type=Path)
    rotate.add_argument("--angle", type=int, required=True, choices=[-90, 90, 180])
    rotate.add_argument("--pages", type=int, nargs="*", help="páginas 1-N (por defecto, todas)")
    rotate.add_argument("--output", type=Path, help="ruta de salida")
    rotate.set_defaults(func=cmd_rotate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(
        level=logging.DEBUG if args.verbose else logging.INFO,
        log_file=getattr(args, "log_file", None),
    )

    if getattr(args, "folder", None) is not None and not args.folder.is_dir():
        print(f"No es una carpeta válida: {args.folder}", file=sys.stderr)
        return EXIT_FAILED

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.", file=sys.stderr)
        return EXIT_FAILED
    except Exception as exc:
        logger.exception("Error no controlado")
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
