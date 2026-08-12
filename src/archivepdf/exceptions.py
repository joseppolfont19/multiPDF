"""Domain exceptions.

The core layer never talks to the user: it raises. Presentation layers (GUI,
CLI) decide how to report. This is what makes the core testable and reusable
from a server or a scheduled job.
"""

from __future__ import annotations


class ArchivePdfError(Exception):
    """Base class for every error raised by this package."""


class UnreadableImageError(ArchivePdfError):
    """An image file could not be opened or decoded."""

    def __init__(self, path, original: Exception | None = None) -> None:
        self.path = path
        self.original = original
        super().__init__(f"Imagen dañada o ilegible: {getattr(path, 'name', path)}")


class IntegrityError(ArchivePdfError):
    """A generated PDF does not contain the expected number of pages.

    Raised by Safe Mode, after a failed chunk has already been retried once.
    """


class MissingDependencyError(ArchivePdfError):
    """An optional dependency required for this operation is not installed."""
