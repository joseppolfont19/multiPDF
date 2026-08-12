"""Loading and preparing bundled images for the interface."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from .theme import LOGO_ALPHA_HIGH, LOGO_ALPHA_LOW

logger = logging.getLogger(__name__)


def load_logo_with_transparency(path: Path) -> Image.Image:
    """Load the logo and key out its flat dark background.

    The source artwork sits on an opaque dark rectangle. Rendered as-is over
    the app background, that rectangle shows as a visible box. Mapping
    luminance to alpha removes it, with a soft ramp between the two
    thresholds so edges stay anti-aliased instead of jagged.

    A logo that already carries its own transparency is returned untouched.
    """
    image = Image.open(path)

    if image.mode == "RGBA" and image.getextrema()[3][0] < 255:
        logger.debug("El logo ya tiene canal alfa propio; se respeta")
        return image

    rgb = image.convert("RGB")
    luminance = rgb.convert("L")

    span = LOGO_ALPHA_HIGH - LOGO_ALPHA_LOW
    lut = [
        0 if value <= LOGO_ALPHA_LOW
        else 255 if value >= LOGO_ALPHA_HIGH
        else int((value - LOGO_ALPHA_LOW) / span * 255)
        for value in range(256)
    ]

    rgba = rgb.convert("RGBA")
    rgba.putalpha(luminance.point(lut))
    return rgba
