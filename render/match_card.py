"""
render/match_card.py — PNG match-report card generator for Tennis Umpire Pro.

Renders a professional 1080-px-wide image summarising the completed match.
The card is cropped vertically to its actual content height before saving.

Requires Pillow (``pip install Pillow``).
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

from theme import CardPalette as C
from engine import MatchState
from theme import MatchConfig

logger = logging.getLogger(__name__)

# ── Font paths (DejaVu bundled with most Linux desktops) ──────────────────
_FONT_DIR  = "/usr/share/fonts/truetype/dejavu/"
_F_BOLD    = _FONT_DIR + "DejaVuSerif-Bold.ttf"
_F_REG     = _FONT_DIR + "DejaVuSerif.ttf"
_F_MONO    = _FONT_DIR + "DejaVuSansMono-Bold.ttf"
_F_MONO_R  = _FONT_DIR + "DejaVuSansMono.ttf"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a TrueType font, falling back to the default bitmap font."""
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        logger.warning("Could not load font %s (size %d); using default.", path, size)
        return ImageFont.load_default()


def _draw_stat_bar(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, w: int, h: int,
    v1: int, v2: int,
    c1: Tuple[int, int, int],
    c2: Tuple[int, int, int],
    bg: Tuple[int, int, int],
) -> None:
    """Draw a centred two-sided horizontal bar representing two values.

    Left side (P1) grows leftward from centre; right side (P2) rightward.
    """
    total = max(v1 + v2, 1)
    mid   = x + w // 2
    b1    = int((v1 / total) * (w // 2))
    b2    = int((v2 / total) * (w // 2))

    draw.rectangle([x, y, x + w, y + h], fill=bg)
    if b1 > 0:
        draw.rectangle([mid - b1, y + 2, mid,      y + h - 2], fill=c1)
    if b2 > 0:
        draw.rectangle([mid,      y + 2, mid + b2, y + h - 2], fill=c2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_match_card(
    p1_name: str,
    p2_name: str,
    winner_num: int,
    state: MatchState,
    config: MatchConfig,
    duration: str,
    output_path: str,
) -> str:
    """Render and save a PNG match-report card.

    Args:
        p1_name:     Display name for Player 1.
        p2_name:     Display name for Player 2.
        winner_num:  1 or 2 — which player won the match.
        state:       Final ``MatchState`` snapshot.
        config:      ``MatchConfig`` used for the match.
        duration:    Human-readable elapsed time string (e.g. ``"01:23:45"``).
        output_path: Destination file path (``*.png``).

    Returns:
        The resolved *output_path* on success.

    Raises:
        OSError: if the file cannot be written.
    """
    W, H = 1080, 1600   # canvas; will be cropped to content
    img  = Image.new("RGB", (W, H), color=C.BG)
    d    = ImageDraw.Draw(img)
    s    = state

    # ── Load fonts ────────────────────────────────────────────────────────
    fnt_hero       = _load_font(_F_BOLD,   90)
    fnt_title      = _load_font(_F_BOLD,   28)
    fnt_subtitle   = _load_font(_F_REG,    18)
    fnt_name_big   = _load_font(_F_BOLD,   42)   # reserved for future use
    fnt_name_sm    = _load_font(_F_BOLD,   26)
    fnt_sets       = _load_font(_F_BOLD,   58)
    fnt_set_hist   = _load_font(_F_MONO,   20)
    fnt_stat_label = _load_font(_F_REG,    20)
    fnt_stat_val   = _load_font(_F_MONO,   22)
    fnt_brand      = _load_font(_F_MONO,   15)
    fnt_badge      = _load_font(_F_BOLD,   15)
    fnt_meta       = _load_font(_F_MONO_R, 16)

    # ── Drawing primitives ────────────────────────────────────────────────

    def cx(text: str, font: ImageFont.FreeTypeFont, y: int, color: tuple = C.WHITE) -> None:
        """Draw *text* horizontally centred on the canvas."""
        bb = d.textbbox((0, 0), text, font=font)
        tw = bb[2] - bb[0]
        d.text(((W - tw) // 2, y), text, font=font, fill=color)

    def lx(text: str, font: ImageFont.FreeTypeFont, x: int, y: int, color: tuple = C.WHITE) -> None:
        """Draw *text* left-aligned from *x*."""
        d.text((x, y), text, font=font, fill=color)

    def rx(text: str, font: ImageFont.FreeTypeFont, x: int, y: int, color: tuple = C.WHITE) -> None:
        """Draw *text* right-aligned at *x*."""
        bb = d.textbbox((0, 0), text, font=font)
        tw = bb[2] - bb[0]
        d.text((x - tw, y), text, font=font, fill=color)

    def hline(y: int, color: tuple = C.DIVIDER, width: int = 1) -> None:
        """Draw a horizontal rule inset 60 px from each side."""
        d.line([(60, y), (W - 60, y)], fill=color, width=width)

    # ── Background grid texture ───────────────────────────────────────────
    for gx in range(0, W, 40):
        d.line([(gx, 0), (gx, H)], fill=C.GRID_LINE, width=1)
    for gy in range(0, H, 40):
        d.line([(0, gy), (W, gy)], fill=C.GRID_LINE, width=1)

    # ── Top accent bar ────────────────────────────────────────────────────
    d.rectangle([0, 0, W, 6], fill=C.GREEN)

    # ── App title & timestamp ─────────────────────────────────────────────
    y = 24
    cx("TENNIS  UMPIRE  PRO", fnt_title, y, C.GREEN)
    y += 38
    cx(
        f"MATCH  REPORT  •  {datetime.now().strftime('%d %b %Y  %H:%M')}",
        fnt_meta, y, C.MUTED,
    )
    y += 36
    hline(y, C.DIVIDER)
    y += 16

    # ── Winner badge ──────────────────────────────────────────────────────
    winner_name = p1_name if winner_num == 1 else p2_name
    badge_txt   = "  WINNER  "
    bb          = d.textbbox((0, 0), badge_txt, font=fnt_badge)
    bw, bh      = bb[2] - bb[0] + 24, bb[3] - bb[1] + 14
    bx          = (W - bw) // 2
    d.rounded_rectangle([bx, y, bx + bw, y + bh], radius=6, fill=C.GREEN)
    cx(badge_txt, fnt_badge, y + 6, C.BG)
    y += bh + 14

    cx(winner_name, fnt_hero, y, C.YELLOW)

    # Decorative star cluster
    star_cx = W // 2
    for sx, sy, sr, sc in [
        (star_cx - 220, y + 55, 14, C.YELLOW),
        (star_cx + 220, y + 55, 14, C.YELLOW),
        (star_cx - 195, y + 30,  8, C.GREEN),
        (star_cx + 195, y + 30,  8, C.GREEN),
    ]:
        d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=sc)

    y += 110
    hline(y, C.GREEN, 2)
    y += 20

    # ── Player name cards ─────────────────────────────────────────────────
    PAD   = 60
    CARDW = (W - PAD * 2 - 20) // 2

    for col, (pname, psets, is_winner) in enumerate([
        (p1_name, s.p1_sets, winner_num == 1),
        (p2_name, s.p2_sets, winner_num == 2),
    ]):
        cx_card  = PAD + col * (CARDW + 20)
        card_bg  = C.WINNER_BG if is_winner else C.LOSER_BG
        name_col = C.GREEN if is_winner else C.MUTED
        sets_col = C.YELLOW if is_winner else C.WHITE

        d.rounded_rectangle(
            [cx_card, y, cx_card + CARDW, y + 80],
            radius=10, fill=card_bg,
        )
        # Player name
        name_bb = d.textbbox((0, 0), pname, font=fnt_name_sm)
        nw      = name_bb[2] - name_bb[0]
        nx      = cx_card + (CARDW - nw) // 2
        d.text((nx, y + 14), pname, font=fnt_name_sm, fill=name_col)

        # Set count
        sets_txt = str(psets)
        s_bb     = d.textbbox((0, 0), sets_txt, font=fnt_sets)
        sw       = s_bb[2] - s_bb[0]
        d.text(
            (cx_card + (CARDW - sw) // 2, y + 44),
            sets_txt, font=fnt_sets, fill=sets_col,
        )

    y += 100
    cx("S E T S", fnt_subtitle, y, C.MUTED)
    y += 30

    # ── Set-by-set history ────────────────────────────────────────────────
    if s.set_history:
        cx("   ".join(s.set_history), fnt_set_hist, y, C.BLUE)
        y += 36
    else:
        y += 10

    hline(y, C.DIVIDER)
    y += 20

    # ── Statistics table ──────────────────────────────────────────────────
    cx("MATCH  STATISTICS", fnt_title, y, C.WHITE)
    y += 44

    LX, MID_X = 100, W // 2

    # Header row
    d.rectangle([60, y - 4, W - 60, y + 30], fill=C.CARD)
    lx(p1_name,  fnt_stat_label, LX,        y, C.GREEN)
    rx(p2_name,  fnt_stat_label, W - LX,    y, C.RED)
    cx("STAT",   fnt_stat_label, y, C.MUTED)
    y += 38
    hline(y - 4, C.DIM)

    def _stat_row(label: str, v1: int, v2: int, alt: bool = False) -> None:
        """Render one numeric statistics row with a mini comparison bar."""
        nonlocal y
        row_bg = C.ROW_ALT if alt else C.BG
        d.rectangle([60, y, W - 60, y + 42], fill=row_bg)
        lx(str(v1), fnt_stat_val, LX,     y + 10, C.WHITE)
        rx(str(v2), fnt_stat_val, W - LX, y + 10, C.WHITE)
        cx(label, fnt_stat_label, y + 12, C.MUTED)
        BAR_W = 260
        _draw_stat_bar(
            d, MID_X - BAR_W // 2, y + 32, BAR_W, 10,
            v1, v2, C.GREEN, C.RED, C.DIVIDER,
        )
        y += 52
        hline(y - 4, C.DIM)

    def _stat_row_str(label: str, v1: str, v2: str, alt: bool = False) -> None:
        """Render one string-valued statistics row (no comparison bar)."""
        nonlocal y
        row_bg = C.ROW_ALT if alt else C.BG
        d.rectangle([60, y, W - 60, y + 42], fill=row_bg)
        lx(v1, fnt_stat_val, LX,     y + 10, C.WHITE)
        rx(v2, fnt_stat_val, W - LX, y + 10, C.WHITE)
        cx(label, fnt_stat_label, y + 12, C.MUTED)
        y += 52
        hline(y - 4, C.DIM)

    _stat_row("Aces",          s.p1_aces,         s.p2_aces,         alt=False)
    _stat_row("Double Faults", s.p1_double_faults, s.p2_double_faults, alt=True)
    _stat_row_str(
        "Break Pts  W/C",
        f"{s.p1_bp_won}/{s.p1_bp_created}",
        f"{s.p2_bp_won}/{s.p2_bp_created}",
        alt=False,
    )
    _stat_row("Total Points",  s.p1_total_points,  s.p2_total_points,  alt=True)

    y += 10

    # ── Total-points distribution bar ────────────────────────────────────
    d.rectangle([60, y, W - 60, y + 18], fill=C.DIM)
    tot  = max(s.p1_total_points + s.p2_total_points, 1)
    p1w  = int(((W - 120) * s.p1_total_points) / tot)
    d.rectangle([60, y, 60 + p1w, y + 18], fill=C.GREEN)
    cx("Total Points Distribution", fnt_meta, y + 22, C.MUTED)
    lx(str(s.p1_total_points), fnt_meta, 70,      y + 1, C.BG)
    rx(str(s.p2_total_points), fnt_meta, W - 70,  y + 1, C.BG)
    y += 52

    hline(y, C.DIVIDER)
    y += 20

    # ── Match metadata ────────────────────────────────────────────────────
    meta_lines = [
        f"Format :  Best of {config.max_sets} sets   |   Duration :  {duration}",
        f"Set History :  {', '.join(s.set_history) if s.set_history else 'N/A'}",
    ]
    for line in meta_lines:
        cx(line, fnt_meta, y, C.MUTED)
        y += 28

    y += 10
    hline(y, C.DIVIDER)
    y += 20

    # ── Branding footer ───────────────────────────────────────────────────
    d.rectangle([0, H - 50, W, H],      fill=(6,  6, 10))
    d.rectangle([0, H - 50, W, H - 48], fill=C.GREEN)
    cx("MrNaNo   *   N4N0 Staff",           fnt_brand, H - 36, C.MUTED)
    cx("Tennis Umpire Pro  |  Match Card",   fnt_brand, H - 54, C.DIM)

    # ── Crop canvas to content + rebuild footer ───────────────────────────
    crop_y = min(y + 80, H)
    img    = img.crop((0, 0, W, crop_y))
    d2     = ImageDraw.Draw(img)
    FH     = img.height

    d2.rectangle([0, FH - 50, W, FH],      fill=(6,  6, 10))
    d2.rectangle([0, FH - 50, W, FH - 48], fill=C.GREEN)

    def _cx2(text: str, font: ImageFont.FreeTypeFont, oy: int, color: tuple) -> None:
        bb2 = d2.textbbox((0, 0), text, font=font)
        tw2 = bb2[2] - bb2[0]
        d2.text(((W - tw2) // 2, oy), text, font=font, fill=color)

    _cx2("MrNaNo   *   N4N0 Staff",         fnt_brand, FH - 36, C.MUTED)
    _cx2("Tennis Umpire Pro  |  Match Card", fnt_brand, FH - 54, C.DIM)

    img.save(output_path, "PNG", dpi=(150, 150))
    logger.info("Match card saved to %s", output_path)
    return output_path
