"""
components/feed.py — Live activity feed widget for Tennis Umpire Pro.

Displays a scrollable, timestamped log of match events (points, aces,
double faults, change-ends announcements, etc.).
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext

from theme import Theme


class ActivityFeed(scrolledtext.ScrolledText):
    """Auto-scrolling text widget used as a match event log.

    Args:
        parent: Parent tkinter widget.
    """

    def __init__(self, parent: tk.Widget) -> None:
        T = Theme
        super().__init__(
            parent,
            width=80,
            height=5,
            bg=T.BG_FEED,
            fg=T.ACCENT_GREEN,
            font=T.FONT_FEED,
            borderwidth=0,
            insertbackground=T.ACCENT_GREEN,
        )

    def log(self, message: str) -> None:
        """Append a timestamped *message* and scroll to the bottom.

        Args:
            message: Plain-text event description.
        """
        ts = datetime.now().strftime("%H:%M:%S")
        self.insert(tk.END, f"[{ts}]  {message}\n")
        self.see(tk.END)
