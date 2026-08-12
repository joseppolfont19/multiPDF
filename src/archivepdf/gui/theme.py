"""Visual language of the application: one place, one meaning per colour.

Semantic rule
-------------
* INDIGO  -> the single real "primary" action (Start / Create / Save)
* BLUE    -> secondary actions (pick folder, open, navigation) and the
             "selected" state of selectors and segmented controls
* RED     -> rotation actions (neutral, non-destructive) and alerts
* No non-interactive element (cards, separators) uses an accent colour, so
  nothing competes visually with the actual buttons.
"""

from __future__ import annotations

APPEARANCE_MODE = "dark"
DEFAULT_COLOR_THEME = "blue"

# --------------------------------------------------------------------------
# Surfaces
# --------------------------------------------------------------------------

COLOR_BG_PRIMARY = "#121317"         # Main window background
COLOR_BG_PANEL = "#191b20"           # Content panels (cards)
COLOR_BG_PANEL_ALT = "#22242b"       # Alternative surface (inputs, inactive chips)
COLOR_BG_HOVER = "#2b2e37"           # Hover for grey buttons/surfaces

# --------------------------------------------------------------------------
# Accents
# --------------------------------------------------------------------------

COLOR_ACCENT_BLUE = "#4f7df3"        # Secondary actions, selected state
COLOR_ACCENT_BLUE_HOVER = "#3d67d6"
COLOR_ACCENT_BLUE_SOFT = "#243050"   # Very faint blue (informational chips/badges)

COLOR_ACCENT_PRIMARY = "#6c5ce7"     # Indigo - the ONLY primary action (final CTA)
COLOR_ACCENT_PRIMARY_HOVER = "#5b4bd1"

COLOR_ACCENT_GREEN = "#10b981"       # Success confirmations only
COLOR_ACCENT_GREEN_HOVER = "#059669"

COLOR_ACCENT_RED = "#c0392b"         # Earthy red (rotation / non-destructive alerts)
COLOR_ACCENT_RED_HOVER = "#a5321f"

# --------------------------------------------------------------------------
# Borders and text
# --------------------------------------------------------------------------

COLOR_BORDER = "#2c2f37"             # Subtle borders between sections
COLOR_BORDER_STRONG = "#3a3d47"      # Borders of interactive components (inputs)
COLOR_TEXT_PRIMARY = "#eef0f4"
COLOR_TEXT_MUTED = "#8b90a0"
COLOR_TEXT_FAINT = "#5b5f6d"

# --------------------------------------------------------------------------
# Pill navigation
# --------------------------------------------------------------------------

COLOR_NAV_BG = "#1a1c22"             # Navigation capsule background
COLOR_NAV_ACTIVE = "#2a2d36"         # Active tab (neutral, not a full accent)
COLOR_NAV_INACTIVE = "transparent"
COLOR_NAV_HOVER = "#22242b"
COLOR_NAV_TEXT_ACTIVE = "#ffffff"
COLOR_NAV_TEXT_INACTIVE = "#7b7f8c"
COLOR_NAV_INDICATOR = "#4f7df3"

# --------------------------------------------------------------------------
# Segmented selectors (Resolution, Optimisation mode)
#
# A single uniform track colour, so unselected options don't look like
# independent "switched off" buttons.
# --------------------------------------------------------------------------

COLOR_SELECTOR_TRACK = "#1c1e25"
COLOR_SELECTOR_BG = "#1c1e25"

# --------------------------------------------------------------------------
# Preview canvas
# --------------------------------------------------------------------------

COLOR_PREVIEW_BG = "#15161b"
COLOR_PREVIEW_BORDER = "#282a32"

# --------------------------------------------------------------------------
# Window geometry and responsive scaling
# --------------------------------------------------------------------------

WINDOW_TITLE = "MultiPDF Professional IV"
BASE_WINDOW_WIDTH = 1300
BASE_WINDOW_HEIGHT = 950
MIN_WINDOW_WIDTH = 1150
MIN_WINDOW_HEIGHT = 740
MIN_UI_SCALE = 0.80
MAX_UI_SCALE = 1.15
RESIZE_DEBOUNCE_MS = 120
SCALE_CHANGE_THRESHOLD = 0.02

# --------------------------------------------------------------------------
# Bundled assets
# --------------------------------------------------------------------------

ICON_PATH = "cont.ico"
LOGO_PATH = "logo.png"
LOGO_DISPLAY_HEIGHT = 210

# Luminance window used to key out the logo's flat dark background.
LOGO_ALPHA_LOW = 14
LOGO_ALPHA_HIGH = 34

# --------------------------------------------------------------------------
# Misc
# --------------------------------------------------------------------------

SYSTEM_INFO_REFRESH_MS = 2000
