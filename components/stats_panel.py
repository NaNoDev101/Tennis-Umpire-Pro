"""
components/stats_panel.py — Live statistics display for Tennis Umpire Pro.

Renders a monospaced table showing aces, double faults, break points and
total points for both players.
"""

from __future__ import annotations

import tkinter as tk

from theme import Theme


class StatsPanel(tk.Frame):
    """Monospaced statistics table widget.

    Args:
        parent: Parent tkinter widget.
    """

    # Column widths (characters) for consistent alignment
    _LABEL_W  = 22
    _VALUE_W  = 10

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=Theme.BG_CARD, pady=10, padx=20)
        T = Theme

        self._stats_lbl = tk.Label(
            self, text="",
            font=T.FONT_STATS,
            bg=T.BG_CARD, fg=T.FG_SECONDARY,
            justify="center",
        )
        self._stats_lbl.pack()

    def update(
        self,
        p1_aces: int,
        p2_aces: int,
        p1_double_faults: int,
        p2_double_faults: int,
        p1_bp_won: int,
        p1_bp_created: int,
        p2_bp_won: int,
        p2_bp_created: int,
        p1_total_points: int,
        p2_total_points: int,
    ) -> None:
        """Redraw the statistics table with the supplied values."""
        lw = self._LABEL_W
        vw = self._VALUE_W
        p1bp = f"{p1_bp_won}/{p1_bp_created}"
        p2bp = f"{p2_bp_won}/{p2_bp_created}"

        text = (
            f"{'STAT':<{lw}} {'P1':>{vw}} {'P2':>{vw}}\n"
            f"{'Aces':<{lw}} {p1_aces:>{vw}} {p2_aces:>{vw}}\n"
            f"{'Double Faults':<{lw}} {p1_double_faults:>{vw}} {p2_double_faults:>{vw}}\n"
            f"{'Break Pts (W/C)':<{lw}} {p1bp:>{vw}} {p2bp:>{vw}}\n"
            f"{'Total Points':<{lw}} {p1_total_points:>{vw}} {p2_total_points:>{vw}}"
        )
        self._stats_lbl.config(text=text)
