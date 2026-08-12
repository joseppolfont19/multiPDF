"""archive-pdf-toolkit -- batch conversion of digitised archival images to PDF."""

from .config import ConversionConfig
from .exceptions import (
    ArchivePdfError,
    IntegrityError,
    MissingDependencyError,
    UnreadableImageError,
)

__version__ = "5.0.0"

__all__ = [
    "ConversionConfig",
    "ArchivePdfError",
    "IntegrityError",
    "MissingDependencyError",
    "UnreadableImageError",
    "__version__",
]
