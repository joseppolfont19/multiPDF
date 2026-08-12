"""Configuration values and the conversion profile object.

Every magic number that used to live scattered through the monolith is
collected here, named, and documented.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------
# Input formats
# --------------------------------------------------------------------------

IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
)

# --------------------------------------------------------------------------
# Batch sizing
#
# Images are never all held in memory at once: they are processed in chunks,
# each chunk written to its own temporary PDF, and the chunks merged at the
# end. The chunk size trades memory against merge overhead.
#
# NOTE: the original code called these CHUNK_LARGE (150) and CHUNK_SMALL
# (250), which was backwards -- the "large" constant held the *smaller*
# value. The names below describe the *workload*, not the number.
# --------------------------------------------------------------------------

MANY_IMAGES_THRESHOLD = 750
CHUNK_SIZE_MANY_IMAGES = 150   # big job -> smaller chunks -> lower peak RAM
CHUNK_SIZE_FEW_IMAGES = 250    # small job -> bigger chunks -> fewer merges
DEFAULT_CHUNK_SIZE = 150       # fixed size used by the standard profile

# Above this number of images, every chunk and the final PDF are verified
# page by page, and a failing chunk is regenerated once before giving up.
SAFE_MODE_THRESHOLD = 1000

# --------------------------------------------------------------------------
# Resource guard (backpressure)
# --------------------------------------------------------------------------

MAX_CPU_PERCENT = 80
MAX_RAM_PERCENT = 90
RESOURCE_WAIT_SECONDS = 10.0

# --------------------------------------------------------------------------
# Image quality
# --------------------------------------------------------------------------

# JPEG quality applied by the standard (non-compressing) profile.
# Kept at 60 to reproduce the historical output of v4.2 byte for byte.
# See docs/architecture.md -> "Known deviations".
STANDARD_JPEG_QUALITY = 60

QUALITY_PRESETS: dict[str, int] = {
    "Molt Baixa (40%)": 40,
    "Baixa (50%)": 50,
    "Mitjana (65%)": 65,
    "Alta (80%)": 80,
    "Molt Alta (90%)": 90,
}

DPI_OPTIONS = ["72", "96", "150", "200", "300"]
SCALE_OPTIONS = ["50%", "75%", "100%"]

# --------------------------------------------------------------------------
# Recursion
# --------------------------------------------------------------------------

MAX_TREE_DEPTH = 5

# Sub-folder names that mark the recto / verso split of a bound document.
RECTO_DIR = "R"
VERSO_DIR = "V"


def chunk_size_for(total_images: int) -> int:
    """Chunk size for a dynamic (compressed) run."""
    return (
        CHUNK_SIZE_MANY_IMAGES
        if total_images > MANY_IMAGES_THRESHOLD
        else CHUNK_SIZE_FEW_IMAGES
    )


@dataclass(frozen=True)
class ConversionConfig:
    """Everything that distinguishes one conversion profile from another.

    The monolith had two near-identical copies of the whole pipeline -- one
    "standard" and one "compressed". They differed only in the values below,
    so they are now a single pipeline parameterised by this object.
    """

    scale_percent: int = 100
    quality: int = STANDARD_JPEG_QUALITY
    dpi: int | None = None
    output_suffix: str = ""
    chunk_size: int | None = None       # None -> chunk_size_for(total)
    throttle_resources: bool = False

    # ---------------- factories ----------------

    @classmethod
    def standard(cls, halve_resolution: bool = False) -> ConversionConfig:
        """Profile of the "Convertidor" tab: fixed chunks, no DPI metadata."""
        return cls(
            scale_percent=50 if halve_resolution else 100,
            quality=STANDARD_JPEG_QUALITY,
            dpi=None,
            output_suffix="",
            chunk_size=DEFAULT_CHUNK_SIZE,
            throttle_resources=False,
        )

    @classmethod
    def compressed(
        cls,
        dpi: int = 150,
        quality: int = 65,
        scale_percent: int = 100,
    ) -> ConversionConfig:
        """Profile of the "Optimitzador" tab: dynamic chunks + backpressure."""
        return cls(
            scale_percent=scale_percent,
            quality=quality,
            dpi=dpi,
            output_suffix="_comp",
            chunk_size=None,
            throttle_resources=True,
        )

    # ---------------- helpers ----------------

    def resolve_chunk_size(self, total_images: int) -> int:
        return self.chunk_size or chunk_size_for(total_images)

    def output_name(self, folder_name: str) -> str:
        return f"{folder_name}{self.output_suffix}.pdf"
