"""Heuristics that turn "how heavy is this batch?" into concrete settings.

Rules live in a table instead of an if/elif ladder, so a new tier is one row
and the whole thing stays trivially testable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Recommendation:
    """A suggested compression profile plus the text shown to the user."""

    dpi: str
    quality: str
    scale: str
    info: str
    estimated_mb: float | None = None


@dataclass(frozen=True)
class _Tier:
    max_mb: float
    dpi: str
    quality: str
    scale: str
    ratio: float | None          # None -> no compression needed
    headline: str
    detail: str


# Ordered from lightest to heaviest batch. The first tier whose ``max_mb``
# exceeds the batch weight wins.
TIERS: tuple[_Tier, ...] = (
    _Tier(
        max_mb=100,
        dpi="150", quality="Alta (80%)", scale="100%", ratio=None,
        headline="✅  El pes és molt acceptable. No cal comprimir.",
        detail="Pots convertir amb qualitat alta sense cap problema.",
    ),
    _Tier(
        max_mb=400,
        dpi="150", quality="Mitjana (65%)", scale="100%", ratio=0.65,
        headline="💡  Compressió lleugera recomanada",
        detail="Qualitat bona, lleument reduïda. Ideal per compartir.",
    ),
    _Tier(
        max_mb=800,
        dpi="96", quality="Baixa (50%)", scale="75%", ratio=0.40,
        headline="⚠️   Compressió moderada recomanada",
        detail="Bon equilibri entre qualitat i mida de fitxer.",
    ),
    _Tier(
        max_mb=float("inf"),
        dpi="72", quality="Molt Baixa (40%)", scale="50%", ratio=0.30,
        headline="🔴  Compressió forta recomanada",
        detail="Reducció significativa; qualitat acceptable per pantalla.",
    ),
)


def format_size(total_mb: float) -> str:
    """Human-readable size, switching to GB past 1000 MB."""
    if total_mb < 1000:
        return f"{total_mb:.1f} MB"
    return f"{total_mb / 1024:.2f} GB"


def recommend_settings(total_mb: float, image_count: int) -> Recommendation:
    """Suggest DPI / quality / scale for a batch of a given weight."""
    tier = next(t for t in TIERS if total_mb < t.max_mb)

    header = f"📦  {image_count} imatges  |  Pes total: {format_size(total_mb)}"
    if tier.ratio is None:
        estimated = None
        headline = tier.headline
    else:
        estimated = total_mb * tier.ratio
        headline = f"{tier.headline}  →  ~{estimated:.0f} MB estimats."

    logger.debug(
        "Recomendación para %.1f MB / %d imágenes: dpi=%s quality=%s scale=%s",
        total_mb, image_count, tier.dpi, tier.quality, tier.scale,
    )

    return Recommendation(
        dpi=tier.dpi,
        quality=tier.quality,
        scale=tier.scale,
        info=f"{header}\n{headline}\n{tier.detail}",
        estimated_mb=estimated,
    )
