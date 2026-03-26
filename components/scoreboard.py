"""
components/scoreboard.py — Scoreboard display component for Tennis Umpire Pro.

Encapsulates the sets label, games label, point-score label, break-point
indicator, and both player name cards with their serving-dot indicators.
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional

from theme import Theme


class Scoreboard(tk.Frame):
    """Composite widget that shows the full current score.

    Hierarchy::

        Scoreboard (Frame)
        ├── set_lbl         — "2 – 1"
        ├── notify_lbl      — "CHANGE ENDS" / "" (temporary banner)
        ├── name_frame      — player name cards with serving dots
        │   ├── p1_name_frame
        │   └── p2_name_frame
        ├── games_frame     — "4 – 3"
        ├── score_lbl       — "ADV  Federer" / "40 – 30"
        └── bp_indicator_lbl — "BREAK POINT — Djokovic"

    Public ``tk.Label`` references are stored as instance attributes so that
    :class:`~ui.TennisUI` can update them directly.
    """

    def __init__(self, parent: tk.Widget, p1_name: str, p2_name: str) -> None:
        super().__init__(parent, bg=Theme.BG_MAIN)
        T = Theme
        self._notify_after_id: Optional[str] = None

        # ── Sets ──────────────────────────────────────────────────────────
        self.set_lbl = tk.Label(
            self, text="0  –  0",
            font=T.FONT_SETS, bg=T.BG_MAIN, fg=T.ACCENT_BLUE,
        )
        self.set_lbl.pack(pady=(6, 0))

        # ── Notification banner ───────────────────────────────────────────
        self.notify_lbl = tk.Label(
            self, text="",
            font=T.FONT_NOTIFY, bg=T.BG_MAIN, fg=T.ACCENT_YELLOW,
        )
        self.notify_lbl.pack()

        # ── Player name cards ─────────────────────────────────────────────
        name_row = tk.Frame(self, bg=T.BG_MAIN)
        name_row.pack(fill="x", padx=60, pady=(4, 0))

        self.p1_name_frame = tk.Frame(name_row, bg=T.BG_MAIN, padx=12, pady=6)
        self.p1_name_frame.pack(side="left", expand=True, fill="both")

        self.p1_server_dot = tk.Label(
            self.p1_name_frame, text="●",
            font=("Courier New", 14, "bold"),
            bg=T.BG_MAIN, fg=T.ACCENT_GREEN,
        )
        self.p1_server_dot.pack(side="left")

        self.p1_name_lbl = tk.Label(
            self.p1_name_frame, text=p1_name,
            font=T.FONT_NAMES, bg=T.BG_MAIN, fg=T.FG_PRIMARY,
        )
        self.p1_name_lbl.pack(side="left", padx=(4, 0))

        tk.Label(name_row, text="vs", font=T.FONT_LABEL,
                 bg=T.BG_MAIN, fg=T.FG_MUTED).pack(side="left", expand=True)

        self.p2_name_frame = tk.Frame(name_row, bg=T.BG_MAIN, padx=12, pady=6)
        self.p2_name_frame.pack(side="right", expand=True, fill="both")

        self.p2_name_lbl = tk.Label(
            self.p2_name_frame, text=p2_name,
            font=T.FONT_NAMES, bg=T.BG_MAIN, fg=T.FG_PRIMARY,
        )
        self.p2_name_lbl.pack(side="right", padx=(0, 4))

        self.p2_server_dot = tk.Label(
            self.p2_name_frame, text="●",
            font=("Courier New", 14, "bold"),
            bg=T.BG_MAIN, fg=T.ACCENT_GREEN,
        )
        self.p2_server_dot.pack(side="right")

        # ── Games ─────────────────────────────────────────────────────────
        games_frame = tk.Frame(self, bg=T.BG_CARD, pady=4)
        games_frame.pack(fill="x", padx=60, pady=(4, 0))

        self.games_lbl = tk.Label(
            games_frame, text="0  –  0",
            font=T.FONT_GAMES, bg=T.BG_CARD, fg=T.ACCENT_YELLOW,
        )
        self.games_lbl.pack()

        # ── Point score (large) ───────────────────────────────────────────
        self.score_lbl = tk.Label(
            self, text="0  –  0",
            font=T.FONT_SCORE, bg=T.BG_MAIN, fg=T.FG_PRIMARY,
        )
        self.score_lbl.pack(pady=(6, 0))

        # ── Break-point indicator ─────────────────────────────────────────
        self.bp_indicator_lbl = tk.Label(
            self, text="",
            font=("Georgia", 13, "bold"),
            bg=T.BG_MAIN, fg=T.ACCENT_RED,
        )
        self.bp_indicator_lbl.pack()

    # ── Update methods ────────────────────────────────────────────────────

    def update_sets(self, p1_sets: int, p2_sets: int) -> None:
        self.set_lbl.config(text=f"{p1_sets}  –  {p2_sets}")

    def update_games(self, p1_games: int, p2_games: int) -> None:
        self.games_lbl.config(text=f"{p1_games}  –  {p2_games}")

    def update_score(self, score_str: str) -> None:
        self.score_lbl.config(text=score_str)

    def update_server(self, current_server: int) -> None:
        """Highlight the name card of whichever player is currently serving."""
        T = Theme
        for player, name_frame, dot_lbl, name_lbl in [
            (1, self.p1_name_frame, self.p1_server_dot, self.p1_name_lbl),
            (2, self.p2_name_frame, self.p2_server_dot, self.p2_name_lbl),
        ]:
            is_server = (player == current_server)
            name_frame.config(bg=T.SERVER_BG    if is_server else T.BG_MAIN)
            dot_lbl.config(
                bg=T.SERVER_BG if is_server else T.BG_MAIN,
                fg=T.SERVER_FG if is_server else T.BG_MAIN,   # hide dot when not serving
            )
            name_lbl.config(
                bg=T.SERVER_BG   if is_server else T.BG_MAIN,
                fg=T.SERVER_FG   if is_server else T.NONSERVER_FG,
            )

    def update_break_point(self, bp_player: Optional[int], bp_name: str) -> None:
        """Show or hide the break-point indicator.

        Args:
            bp_player: Player number with the BP, or ``None``.
            bp_name:   Display name of *bp_player* (ignored when ``None``).
        """
        if bp_player is not None:
            self.bp_indicator_lbl.config(text=f"BREAK POINT  —  {bp_name}")
        else:
            self.bp_indicator_lbl.config(text="")

    def show_notify(self, text: str, clear_after: int = 2500) -> None:
        """Display a temporary notification banner.

        Args:
            text:        Banner text to show.
            clear_after: Milliseconds before the banner is hidden.
        """
        self.notify_lbl.config(text=f"  ⚑  {text}  ⚑  ")
        if self._notify_after_id:
            self.after_cancel(self._notify_after_id)
        self._notify_after_id = self.after(
            clear_after, lambda: self.notify_lbl.config(text="")
        )
