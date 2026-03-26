"""
ui.py — Main application view for Tennis Umpire Pro.

:class:`TennisUI` owns the root ``tk.Tk`` window and wires together
the sub-components (scoreboard, controls, stats, feed) with the
:class:`~engine.MatchEngine` via the event bus.

Responsibilities:
* Build and lay out the window and all sub-components.
* Subscribe to engine events and dispatch to the correct handler.
* Coordinate file save/load dialogs and error reporting.
* Drive the elapsed-time clock.
* Trigger the PNG match-card generation on match completion.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from tkinter import Menu, filedialog, messagebox
import tkinter as tk
from typing import Optional

from engine import Event, MatchEngine
from theme import MatchConfig, Theme
from utils.sound import SoundManager
from render.match_card import generate_match_card
from components.scoreboard import Scoreboard
from components.controls import ControlsPanel
from components.stats_panel import StatsPanel
from components.feed import ActivityFeed

logger = logging.getLogger(__name__)


class TennisUI:
    """Main application window for Tennis Umpire Pro.

    Args:
        root:   The root ``tk.Tk`` instance.
        engine: Fully initialised :class:`~engine.MatchEngine`.
        config: The :class:`~theme.MatchConfig` for the current match.
    """

    def __init__(self, root: tk.Tk, engine: MatchEngine, config: MatchConfig) -> None:
        self.root       = root
        self.engine     = engine
        self.config     = config
        self.sound      = SoundManager(config.sound_enabled)
        self.start_time = time.time()

        self._setup_window()
        self._build_menu()
        self._build_header()
        self._build_scoreboard()
        self._build_stats()
        self._build_feed()
        self._build_controls()
        self._build_footer()

        self._subscribe_to_events()
        self._bind_keys()
        self._tick_clock()
        self.refresh_ui()

    # ──────────────────────────────────────────────────────────────────────
    # Window & layout construction
    # ──────────────────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        T = Theme
        self.root.title("Tennis Umpire Pro")
        self.root.geometry("960x1020")
        self.root.configure(bg=T.BG_MAIN)
        self.root.resizable(False, False)

    def _build_menu(self) -> None:
        T = Theme
        menubar = Menu(self.root, bg=T.BG_PANEL, fg=T.FG_PRIMARY, relief="flat")

        file_menu = Menu(menubar, tearoff=0, bg=T.BG_PANEL, fg=T.FG_PRIMARY)
        file_menu.add_command(label="Save Match", command=self._save_match)
        file_menu.add_command(label="Load Match", command=self._load_match)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        settings_menu = Menu(menubar, tearoff=0, bg=T.BG_PANEL, fg=T.FG_PRIMARY)
        settings_menu.add_command(label="Toggle Sound", command=self._toggle_sound)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        self.root.config(menu=menubar)

    def _build_header(self) -> None:
        T = Theme
        tk.Label(
            self.root,
            text="TENNIS  UMPIRE  PRO",
            font=T.FONT_TITLE, bg=T.BG_MAIN, fg=T.ACCENT_GREEN,
        ).pack(pady=(14, 0))

        tk.Label(
            self.root,
            text="by  MrNaNo  ✦  N4N0 Staff",
            font=("Courier New", 9, "bold"),
            bg=T.BG_MAIN, fg=T.ACCENT_BLUE,
        ).pack(pady=(0, 2))

        self.timer_lbl = tk.Label(
            self.root,
            text="00:00:00",
            font=T.FONT_CLOCK, bg=T.BG_MAIN, fg=T.FG_MUTED,
        )
        self.timer_lbl.pack()

    def _build_scoreboard(self) -> None:
        self.scoreboard = Scoreboard(
            self.root,
            p1_name=self.config.p1_name,
            p2_name=self.config.p2_name,
        )
        self.scoreboard.pack(fill="x")

    def _build_stats(self) -> None:
        self.stats_panel = StatsPanel(self.root)
        self.stats_panel.pack(fill="x", padx=60, pady=(6, 4))

    def _build_feed(self) -> None:
        self.feed = ActivityFeed(self.root)
        self.feed.pack(padx=60, pady=(0, 8))

    def _build_controls(self) -> None:
        controls_frame = tk.Frame(self.root, bg=Theme.BG_MAIN)
        controls_frame.pack(pady=4)

        self.controls = ControlsPanel(
            controls_frame,
            p1_name=self.config.p1_name,
            p2_name=self.config.p2_name,
            on_score=self._handle_score,
            on_undo=self._handle_undo,
        )
        self.controls.pack()

    def _build_footer(self) -> None:
        tk.Label(
            self.root,
            text="⚡  MrNaNo  ✦  N4N0 Staff  ⚡",
            font=("Courier New", 8, "bold"),
            bg=Theme.BG_MAIN, fg=Theme.FG_MUTED,
        ).pack(pady=(0, 8))

    # ──────────────────────────────────────────────────────────────────────
    # Event wiring
    # ──────────────────────────────────────────────────────────────────────

    def _subscribe_to_events(self) -> None:
        e = self.engine.events
        e.on(Event.REFRESH,        self.refresh_ui)
        e.on(Event.GAME_WON,       self._on_game_won)
        e.on(Event.SET_WON,        self._on_set_won)
        e.on(Event.MATCH_FINISHED, self._on_match_finished)
        e.on(Event.TIEBREAK_START, self._on_tiebreak_start)
        e.on(Event.CHANGE_ENDS,    self._on_change_ends)

    def _bind_keys(self) -> None:
        self.root.bind("<Left>", lambda _: self._handle_score(1))
        self.root.bind("<Right>", lambda _: self._handle_score(2))
        self.root.bind("u", lambda _: self._handle_undo())
        self.root.bind("U", lambda _: self._handle_undo())
        self.root.focus_set()

    # ──────────────────────────────────────────────────────────────────────
    # Engine event handlers
    # ──────────────────────────────────────────────────────────────────────

    def _on_game_won(self, player: int) -> None:
        self.feed.log(f"Game → {self._player_name(player)}")
        self.sound.play("game")

    def _on_set_won(self, player: int) -> None:
        s = self.engine.state
        self.feed.log(
            f"Set won by {self._player_name(player)}  |  "
            f"Sets: {s.p1_sets}–{s.p2_sets}"
        )
        self.sound.play("set")

    def _on_match_finished(self, player: int) -> None:
        self.sound.play("match")
        self.refresh_ui()
        self._export_and_close(player)

    def _on_tiebreak_start(self) -> None:
        self.feed.log("⚡  TIEBREAK  ⚡")
        self.scoreboard.show_notify("TIEBREAK", clear_after=4000)

    def _on_change_ends(self) -> None:
        self.feed.log("↕  Change Ends")
        self.scoreboard.show_notify("CHANGE ENDS", clear_after=3000)

    # ──────────────────────────────────────────────────────────────────────
    # User-action handlers
    # ──────────────────────────────────────────────────────────────────────

    def _handle_score(
        self,
        player: int,
        ace: bool = False,
        df: bool = False,
    ) -> None:
        """Route a user scoring action to the engine and update the feed."""
        self.engine.score_point(player, is_ace=ace, is_double_fault=df)
        if ace:
            self.feed.log(f"Ace — {self._player_name(player)}")
        elif df:
            self.feed.log(f"Double Fault — {self._player_name(player)}")
        self.sound.play("point")

    def _handle_undo(self) -> None:
        if self.engine.undo():
            self.feed.log(f"← Undo #{self.engine.state.undo_count}")
        else:
            self.feed.log("Nothing to undo.")

    # ──────────────────────────────────────────────────────────────────────
    # UI refresh
    # ──────────────────────────────────────────────────────────────────────

    def refresh_ui(self) -> None:
        """Synchronise every display element with the current engine state."""
        s = self.engine.state

        self.scoreboard.update_sets(s.p1_sets, s.p2_sets)
        self.scoreboard.update_games(s.p1_games, s.p2_games)
        self.scoreboard.update_score(self.engine.get_score_str())
        self.scoreboard.update_server(s.current_server)

        bp_player = self.engine.is_break_point()
        bp_name   = self._player_name(bp_player) if bp_player else ""
        self.scoreboard.update_break_point(bp_player, bp_name)

        self.stats_panel.update(
            p1_aces=s.p1_aces,
            p2_aces=s.p2_aces,
            p1_double_faults=s.p1_double_faults,
            p2_double_faults=s.p2_double_faults,
            p1_bp_won=s.p1_bp_won,
            p1_bp_created=s.p1_bp_created,
            p2_bp_won=s.p2_bp_won,
            p2_bp_created=s.p2_bp_created,
            p1_total_points=s.p1_total_points,
            p2_total_points=s.p2_total_points,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Clock
    # ──────────────────────────────────────────────────────────────────────

    def _tick_clock(self) -> None:
        """Update the elapsed-time label and reschedule itself every second."""
        elapsed = int(time.time() - self.start_time)
        self.timer_lbl.config(text=time.strftime("%H:%M:%S", time.gmtime(elapsed)))
        self.root.after(1000, self._tick_clock)

    # ──────────────────────────────────────────────────────────────────────
    # File operations
    # ──────────────────────────────────────────────────────────────────────

    def _save_match(self) -> None:
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not filename:
            return
        try:
            self.engine.save_state(filename)
            self.feed.log(f"Match saved → {os.path.basename(filename)}")
        except OSError as exc:
            logger.error("Save failed: %s", exc)
            messagebox.showerror("Save Error", f"Could not save match:\n{exc}")

    def _load_match(self) -> None:
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if not filename:
            return
        try:
            self.engine.load_state(filename)
            self.feed.log(f"Match loaded ← {os.path.basename(filename)}")
        except FileNotFoundError:
            messagebox.showerror("Load Error", f"File not found:\n{filename}")
        except (KeyError, ValueError, TypeError) as exc:
            logger.error("Load failed (corrupt file?): %s", exc)
            messagebox.showerror(
                "Load Error",
                f"The file appears to be corrupt or incompatible:\n{exc}",
            )
        except OSError as exc:
            logger.error("Load failed: %s", exc)
            messagebox.showerror("Load Error", f"Could not open file:\n{exc}")

    def _toggle_sound(self) -> None:
        self.config.sound_enabled = not self.config.sound_enabled
        self.sound.enabled = self.config.sound_enabled
        state = "enabled" if self.config.sound_enabled else "disabled"
        messagebox.showinfo("Settings", f"Sound {state}.")

    # ──────────────────────────────────────────────────────────────────────
    # Match-end report
    # ──────────────────────────────────────────────────────────────────────

    def _export_and_close(self, winner_num: int) -> None:
        """Generate the PNG match card, show a summary dialog, then close."""
        s, c  = self.engine.state, self.engine.config
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        png_fname = f"Match_Report_{stamp}.png"

        try:
            png_path = generate_match_card(
                p1_name=c.p1_name,
                p2_name=c.p2_name,
                winner_num=winner_num,
                state=s,
                config=c,
                duration=self.timer_lbl.cget("text"),
                output_path=png_fname,
            )
            card_msg = f"\nMatch card saved:\n{png_path}"
        except Exception as exc:
            logger.exception("Failed to generate match card: %s", exc)
            card_msg = "\n(Match card could not be generated.)"

        winner_name = self._player_name(winner_num)
        messagebox.showinfo(
            "Match Finished",
            f"Winner: {winner_name}\n\n"
            f"Final Sets: {s.p1_sets} – {s.p2_sets}"
            f"{card_msg}",
        )
        self.root.destroy()

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _player_name(self, player: int) -> str:
        """Return the display name for *player* (1 or 2)."""
        return self.config.p1_name if player == 1 else self.config.p2_name
