"""
components/controls.py — Button control panel for Tennis Umpire Pro.

Contains all scoring buttons (point, ace, double-fault) and the undo
button.  Keyboard hints are also rendered here.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from theme import Theme


class ControlsPanel(tk.Frame):
    """Scoring action buttons laid out in two rows.

    Row 1: P1 Point  |  Undo  |  P2 Point
    Row 2: Ace(P1)  DblFault(P1)  Ace(P2)  DblFault(P2)

    Args:
        parent:   Parent tkinter widget.
        p1_name:  Display name for Player 1 (used in button labels).
        p2_name:  Display name for Player 2 (used in button labels).
        on_score: Callback ``(player: int, ace: bool, df: bool) -> None``.
        on_undo:  Callback ``() -> None``.
    """

    def __init__(
        self,
        parent: tk.Widget,
        p1_name: str,
        p2_name: str,
        on_score: Callable[[int, bool, bool], None],
        on_undo: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg=Theme.BG_MAIN)
        T = Theme

        # ── Row 1: main point buttons ──────────────────────────────────
        row1 = tk.Frame(self, bg=T.BG_MAIN)
        row1.pack(pady=4)

        self._make_btn(
            row1, f"◀  {p1_name}  Point",
            T.ACCENT_GREEN, "#0a0a0f",
            lambda: on_score(1, False, False),
            row=0, col=0, width=22,
        )
        self._make_btn(
            row1, "⟵  UNDO  ⟶",
            "#333344", T.FG_SECONDARY,
            on_undo,
            row=0, col=1, width=14,
        )
        self._make_btn(
            row1, f"{p2_name}  Point  ▶",
            T.ACCENT_RED, "#0a0a0f",
            lambda: on_score(2, False, False),
            row=0, col=2, width=22,
        )

        # ── Row 2: ace / double-fault buttons ─────────────────────────
        row2 = tk.Frame(self, bg=T.BG_MAIN)
        row2.pack(pady=2)

        self._make_btn(
            row2, f"Ace  ({p1_name})",
            "#1a3a2a", T.ACCENT_GREEN,
            lambda: on_score(1, True, False),
            row=0, col=0, width=20, font=T.FONT_BTN_SM,
        )
        self._make_btn(
            row2, f"Dbl Fault  ({p1_name})",
            "#3a1a1a", T.ACCENT_RED,
            lambda: on_score(1, False, True),
            row=0, col=1, width=20, font=T.FONT_BTN_SM,
        )
        self._make_btn(
            row2, f"Ace  ({p2_name})",
            "#1a3a2a", T.ACCENT_GREEN,
            lambda: on_score(2, True, False),
            row=0, col=2, width=20, font=T.FONT_BTN_SM,
        )
        self._make_btn(
            row2, f"Dbl Fault  ({p2_name})",
            "#3a1a1a", T.ACCENT_RED,
            lambda: on_score(2, False, True),
            row=0, col=3, width=20, font=T.FONT_BTN_SM,
        )

        # ── Keyboard hint ──────────────────────────────────────────────
        tk.Label(
            self,
            text="← / → to score  |  U to undo",
            font=("Courier New", 9),
            bg=T.BG_MAIN, fg=T.FG_MUTED,
        ).pack(pady=(2, 2))

    # ── Internal helper ────────────────────────────────────────────────

    @staticmethod
    def _make_btn(
        parent: tk.Widget,
        text: str,
        bg: str,
        fg: str,
        cmd: Callable,
        row: int,
        col: int,
        width: int = 15,
        font: tuple | None = None,
        padx: int = 5,
        pady: int = 3,
    ) -> tk.Button:
        """Create and grid a styled flat button.

        Returns:
            The created :class:`tk.Button` instance.
        """
        font = font or Theme.FONT_BTN
        btn = tk.Button(
            parent,
            text=text,
            bg=bg, fg=fg,
            width=width,
            font=font,
            command=cmd,
            relief="flat",
            activebackground=fg,
            activeforeground=bg,
            cursor="hand2",
            pady=pady,
        )
        btn.grid(row=row, column=col, padx=padx, pady=2)
        return btn
