"""
theme.py — Visual theme and match configuration for Tennis Umpire Pro.

Separating theme data from application logic allows future support for
multiple themes (dark / light / high-contrast) without touching UI code.
"""

from dataclasses import dataclass
from typing import Tuple


# ---------------------------------------------------------------------------
# Colour / font constants
# ---------------------------------------------------------------------------

ColorRGB = Tuple[int, int, int]


class Theme:
    """Dark-court aesthetic — all UI colours and fonts in one place.

    To add a second theme, subclass ``Theme`` and override the class
    attributes you want to change, then pass the subclass wherever
    ``Theme`` is imported.
    """

    # ── Background palette ──────────────────────────────────────────────
    BG_MAIN: str       = "#0a0a0f"
    BG_PANEL: str      = "#111118"
    BG_CARD: str       = "#16161f"
    BG_FEED: str       = "#0d0d14"

    # ── Accent colours ──────────────────────────────────────────────────
    ACCENT_GREEN: str  = "#00e676"
    ACCENT_YELLOW: str = "#ffd740"
    ACCENT_RED: str    = "#ff5252"
    ACCENT_BLUE: str   = "#40c4ff"

    # ── Foreground palette ──────────────────────────────────────────────
    FG_PRIMARY: str    = "#e8e8f0"
    FG_SECONDARY: str  = "#9090aa"
    FG_MUTED: str      = "#44445a"

    # ── Serving player highlight ─────────────────────────────────────────
    SERVER_BG: str     = "#1a2e1a"
    SERVER_FG: str     = "#00e676"
    NONSERVER_BG: str  = BG_MAIN
    NONSERVER_FG: str  = "#9090aa"

    # ── Fonts ────────────────────────────────────────────────────────────
    FONT_TITLE: tuple  = ("Georgia",     30, "bold")
    FONT_CLOCK: tuple  = ("Courier New", 11)
    FONT_SCORE: tuple  = ("Georgia",    120, "bold")
    FONT_GAMES: tuple  = ("Georgia",     52, "bold")
    FONT_SETS: tuple   = ("Georgia",     36, "bold")
    FONT_NAMES: tuple  = ("Georgia",     18, "bold")
    FONT_STATS: tuple  = ("Courier New", 10)
    FONT_FEED: tuple   = ("Courier New",  9)
    FONT_BTN: tuple    = ("Georgia",     11, "bold")
    FONT_BTN_SM: tuple = ("Courier New",  9, "bold")
    FONT_LABEL: tuple  = ("Georgia",     11)
    FONT_NOTIFY: tuple = ("Georgia",     14, "bold")


# ---------------------------------------------------------------------------
# PNG card colour palette (PIL/Pillow uses RGB tuples)
# ---------------------------------------------------------------------------

class CardPalette:
    """Colour constants used by the PNG match-card renderer."""

    BG:        ColorRGB = (10,  10,  15)
    CARD:      ColorRGB = (18,  18,  28)
    DIVIDER:   ColorRGB = (30,  30,  50)
    GREEN:     ColorRGB = (0,  230, 118)
    YELLOW:    ColorRGB = (255, 215,  64)
    RED:       ColorRGB = (255,  82,  82)
    BLUE:      ColorRGB = (64,  196, 255)
    WHITE:     ColorRGB = (232, 232, 240)
    MUTED:     ColorRGB = (120, 120, 160)
    DIM:       ColorRGB = (50,   50,  75)
    WINNER_BG: ColorRGB = (0,   40,  20)
    LOSER_BG:  ColorRGB = (25,  18,  18)
    GRID_LINE: ColorRGB = (15,  15,  22)
    ROW_ALT:   ColorRGB = (14,  14,  22)


# ---------------------------------------------------------------------------
# Match configuration
# ---------------------------------------------------------------------------

@dataclass
class MatchConfig:
    """User-supplied match settings collected at startup."""

    p1_name: str       = "Player 1"
    p2_name: str       = "Player 2"
    max_sets: int      = 3         # 3 or 5
    tiebreak_at: int   = 6         # games-per-set before tiebreak
    sound_enabled: bool = True
