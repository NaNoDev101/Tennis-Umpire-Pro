"""
main.py — Entry point for Tennis Umpire Pro.

Presents a short setup dialog to collect player names and match settings,
then launches the main UI window.

Usage::

    python main.py
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, simpledialog

from engine import MatchEngine
from theme import MatchConfig
from ui import TennisUI

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Startup dialog
# ---------------------------------------------------------------------------

def _collect_config(root: tk.Tk) -> MatchConfig:
    """Show setup dialogs and return a populated :class:`~theme.MatchConfig`.

    Args:
        root: A hidden (withdrawn) ``tk.Tk`` instance used to anchor the
              dialogs.

    Returns:
        A fully populated ``MatchConfig``.
    """
    p1 = (
        simpledialog.askstring("Setup", "Player 1 Name:", initialvalue="Player 1")
        or "Player 1"
    )
    p2 = (
        simpledialog.askstring("Setup", "Player 2 Name:", initialvalue="Player 2")
        or "Player 2"
    )

    sets = simpledialog.askinteger(
        "Settings", "Best of (3 or 5 sets)?",
        initialvalue=3, minvalue=3, maxvalue=5,
    )
    if sets not in (3, 5):
        sets = 3

    tb = simpledialog.askinteger(
        "Settings", "Games per set before Tiebreak?",
        initialvalue=6, minvalue=2,
    )
    if not tb:
        tb = 6

    sound = messagebox.askyesno("Settings", "Enable sound notifications?")

    return MatchConfig(
        p1_name=p1,
        p2_name=p2,
        max_sets=sets,
        tiebreak_at=tb,
        sound_enabled=sound,
    )


# ---------------------------------------------------------------------------
# Application bootstrap
# ---------------------------------------------------------------------------

def startup() -> None:
    """Bootstrap the application: collect config, create engine, show UI."""
    root = tk.Tk()
    root.withdraw()   # hide root while showing setup dialogs

    config = _collect_config(root)
    engine = MatchEngine(config)
    logger.info(
        "Starting match: %s vs %s  (best of %d, tiebreak at %d)",
        config.p1_name, config.p2_name, config.max_sets, config.tiebreak_at,
    )

    root.deiconify()
    TennisUI(root, engine, config)
    root.mainloop()


if __name__ == "__main__":
    startup()
