import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
import subprocess
import logging
import copy
import time
from dataclasses import dataclass, field
from datetime import datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
POINTS = ["0", "15", "30", "40"]
SOUNDS = {"point": "audio-volume-change", "game": "complete", "match": "dialog-information"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------
@dataclass
class MatchState:
    p1_sets: int = 0
    p2_sets: int = 0
    p1_games: int = 0
    p2_games: int = 0
    p1_points: int = 0
    p2_points: int = 0
    is_tiebreak: bool = False
    current_server: int = 1
    p1_total_points: int = 0
    p2_total_points: int = 0
    set_history: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Match Engine  (pure logic, no UI)
# ---------------------------------------------------------------------------
class MatchEngine:
    """Handles all tennis scoring rules independently of the UI."""

    def __init__(self, max_sets: int = 3, tiebreak_at: int = 6):
        self.max_sets = max_sets
        self.tiebreak_at = tiebreak_at
        self.sets_to_win = max_sets // 2 + 1
        self.state = MatchState()
        self._history: list[MatchState] = []
        self.undo_count = 0
        # Events: UI layer subscribes to these
        self.on_point_scored = None
        self.on_game_won = None
        self.on_tiebreak_start = None
        self.on_set_won = None
        self.on_match_finished = None
        self.on_server_changed = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def score_point(self, player: int) -> bool:
        """Award a point to player (1 or 2). Returns False if match is over."""
        if self.match_finished():
            return False
        self._save_snapshot()

        s = self.state
        if player == 1:
            s.p1_points += 1
            s.p1_total_points += 1
        else:
            s.p2_points += 1
            s.p2_total_points += 1

        if s.is_tiebreak:
            self._handle_tiebreak_serve()
            self._check_tiebreak_win()
        else:
            self._check_game_win()

        logging.info("Point to P%d | Score: %d-%d", player, s.p1_points, s.p2_points)
        if self.on_point_scored:
            self.on_point_scored(player)
        return True

    def undo(self) -> bool:
        """Restore previous state. Returns False if nothing to undo."""
        if not self._history:
            return False
        self.state = self._history.pop()
        self.undo_count += 1
        logging.info("Undo #%d applied", self.undo_count)
        return True

    def match_finished(self) -> bool:
        return (self.state.p1_sets >= self.sets_to_win or
                self.state.p2_sets >= self.sets_to_win)

    def current_score_text(self) -> str:
        s = self.state
        if s.is_tiebreak:
            return f"{s.p1_points} - {s.p2_points}"
        if s.p1_points >= 3 and s.p2_points >= 3:
            if s.p1_points == s.p2_points:
                return "DEUCE"
            return "ADV P1" if s.p1_points > s.p2_points else "ADV P2"
        return f"{POINTS[s.p1_points]} - {POINTS[s.p2_points]}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _save_snapshot(self):
        self._history.append(copy.deepcopy(self.state))

    def _switch_server(self):
        self.state.current_server ^= 3  # toggles 1 ↔ 2
        if self.on_server_changed:
            self.on_server_changed(self.state.current_server)

    def _handle_tiebreak_serve(self):
        total = self.state.p1_points + self.state.p2_points
        # First point: server switches; then every 2 points
        if total == 1 or (total > 1 and total % 2 == 1):
            self._switch_server()

    def _check_game_win(self):
        s = self.state
        if s.p1_points >= 4 and s.p1_points - s.p2_points >= 2:
            self._win_game(1)
        elif s.p2_points >= 4 and s.p2_points - s.p1_points >= 2:
            self._win_game(2)

    def _check_tiebreak_win(self):
        s = self.state
        if s.p1_points >= 7 and s.p1_points - s.p2_points >= 2:
            self._win_game(1)
        elif s.p2_points >= 7 and s.p2_points - s.p1_points >= 2:
            self._win_game(2)

    def _win_game(self, player: int):
        s = self.state
        logging.info("Game won by Player %d", player)
        self._switch_server()
        s.p1_points = 0
        s.p2_points = 0
        if player == 1:
            s.p1_games += 1
        else:
            s.p2_games += 1
        if self.on_game_won:
            self.on_game_won(player)
        self._check_set_win()

    def _check_set_win(self):
        s = self.state
        g1, g2 = s.p1_games, s.p2_games
        tb = self.tiebreak_at

        if (g1 >= tb and g1 - g2 >= 2) or g1 == tb + 1:
            self._win_set(1)
        elif (g2 >= tb and g2 - g1 >= 2) or g2 == tb + 1:
            self._win_set(2)
        elif g1 == tb and g2 == tb:
            s.is_tiebreak = True
            logging.info("Tiebreak started")
            if self.on_tiebreak_start:
                self.on_tiebreak_start()

    def _win_set(self, player: int):
        s = self.state
        s.set_history.append(f"{s.p1_games}-{s.p2_games}")
        logging.info("Set won by Player %d | Sets: %d-%d", player, s.p1_sets, s.p2_sets)
        if player == 1:
            s.p1_sets += 1
        else:
            s.p2_sets += 1
        s.p1_games = 0
        s.p2_games = 0
        s.is_tiebreak = False
        if self.on_set_won:
            self.on_set_won(player)
        if self.match_finished():
            if self.on_match_finished:
                self.on_match_finished(player)


# ---------------------------------------------------------------------------
# UI Layer
# ---------------------------------------------------------------------------
class TennisProApp:
    """Handles all UI; delegates rules to MatchEngine."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Tennis Umpire Pro")
        self.root.geometry("820x980")
        self.root.configure(bg="#0d0d0d")
        self.sound_enabled = True

        # Get player names
        self.p1_name = simpledialog.askstring("Player Names", "Player 1 Name:") or "Player 1"
        self.p2_name = simpledialog.askstring("Player Names", "Player 2 Name:") or "Player 2"

        # Engine
        self.engine = MatchEngine(max_sets=3, tiebreak_at=6)
        self._connect_engine_events()

        self.start_time = time.time()
        self.paused = False

        self._build_ui()
        self.update_clock()
        self.refresh_ui()

    # ------------------------------------------------------------------
    # Engine event wiring
    # ------------------------------------------------------------------
    def _connect_engine_events(self):
        self.engine.on_point_scored = lambda p: self.refresh_ui()
        self.engine.on_game_won = self._on_game_won
        self.engine.on_tiebreak_start = lambda: self.add_feed("!! TIEBREAK !!")
        self.engine.on_set_won = self._on_set_won
        self.engine.on_match_finished = self._on_match_finished
        self.engine.on_server_changed = lambda _: None  # handled in refresh_ui

    def _on_game_won(self, player: int):
        name = self.p1_name if player == 1 else self.p2_name
        self.add_feed(f"Game → {name}")
        self.play_sound("game")

    def _on_set_won(self, player: int):
        name = self.p1_name if player == 1 else self.p2_name
        s = self.engine.state
        self.add_feed(f"Set won by {name}  |  Sets: {s.p1_sets}-{s.p2_sets}")

    def _on_match_finished(self, player: int):
        self.play_sound("match")
        self.refresh_ui()
        s = self.engine.state
        winner = self.p1_name if s.p1_sets > s.p2_sets else self.p2_name
        duration = self.timer_label.cget("text")
        stats = (
            f"Match Over!\n\n"
            f"Winner: {winner}\n"
            f"Sets: {', '.join(s.set_history)}\n"
            f"Total Points: {self.p1_name} ({s.p1_total_points})  -  {self.p2_name} ({s.p2_total_points})\n"
            f"Duration: {duration}\n"
            f"Undos Used: {self.engine.undo_count}"
        )
        logging.info("Match finished. Winner: %s", winner)
        messagebox.showinfo("Match Summary", stats)
        self.root.destroy()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        # Title
        tk.Label(
            self.root, text="TENNIS PRO",
            font=("Impact", 36), bg="#0d0d0d", fg="#00e676"
        ).pack(pady=(14, 0))

        # Timer
        self.timer_label = tk.Label(
            self.root, text="00:00:00",
            font=("Consolas", 13), bg="#0d0d0d", fg="#666"
        )
        self.timer_label.pack()

        # Sets display
        set_frame = tk.Frame(self.root, bg="#0d0d0d")
        set_frame.pack(pady=8)

        self.p1_label = tk.Label(
            set_frame, text="", font=("Arial", 19, "bold"),
            bg="#0d0d0d", fg="white", width=18, anchor="e"
        )
        self.p1_label.grid(row=0, column=0, padx=10)

        self.p2_label = tk.Label(
            set_frame, text="", font=("Arial", 19, "bold"),
            bg="#0d0d0d", fg="white", width=18, anchor="w"
        )
        self.p2_label.grid(row=0, column=1, padx=10)

        self.set_score_val = tk.Label(
            set_frame, text="0 - 0",
            font=("Arial", 44, "bold"), bg="#0d0d0d", fg="#00e676"
        )
        self.set_score_val.grid(row=1, column=0, columnspan=2, pady=6)

        # Games
        self.game_label = tk.Label(
            self.root, text="GAMES: 0 - 0",
            font=("Arial", 27), bg="#0d0d0d", fg="#3498db"
        )
        self.game_label.pack()

        # Point score (big display)
        self.score_display = tk.Label(
            self.root, text="0 - 0",
            font=("Arial", 140, "bold"), bg="#0d0d0d", fg="#f1c40f"
        )
        self.score_display.pack(pady=4)

        # Status bar
        self.status_msg = tk.Label(
            self.root, text="READY",
            font=("Arial", 15, "bold"), bg="#1e1e1e", fg="white", width=42
        )
        self.status_msg.pack(pady=4)

        # Feed
        self.feed = scrolledtext.ScrolledText(
            self.root, width=68, height=7,
            font=("Courier", 11), bg="#111", fg="#00e676", borderwidth=0
        )
        self.feed.pack(pady=8)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#0d0d0d")
        btn_frame.pack(pady=14)

        tk.Button(
            btn_frame, text=self.p1_name,
            font=("Arial", 14, "bold"), width=13, height=2,
            bg="#2ecc71", fg="white",
            command=lambda: self.handle_score(1)
        ).grid(row=0, column=0, padx=8)

        tk.Button(
            btn_frame, text=self.p2_name,
            font=("Arial", 14, "bold"), width=13, height=2,
            bg="#e74c3c", fg="white",
            command=lambda: self.handle_score(2)
        ).grid(row=0, column=1, padx=8)

        self.undo_btn = tk.Button(
            btn_frame, text="UNDO (0)",
            font=("Arial", 13), width=10, height=2,
            bg="#555", fg="white",
            command=self.handle_undo
        )
        self.undo_btn.grid(row=0, column=2, padx=8)

        # Secondary controls
        ctrl_frame = tk.Frame(self.root, bg="#0d0d0d")
        ctrl_frame.pack(pady=4)

        self.pause_btn = tk.Button(
            ctrl_frame, text="⏸ Pause",
            font=("Arial", 11), width=10,
            bg="#333", fg="white",
            command=self.toggle_pause
        )
        self.pause_btn.grid(row=0, column=0, padx=6)

        self.sound_btn = tk.Button(
            ctrl_frame, text="🔊 Sound: ON",
            font=("Arial", 11), width=12,
            bg="#333", fg="white",
            command=self.toggle_sound
        )
        self.sound_btn.grid(row=0, column=1, padx=6)

        tk.Button(
            ctrl_frame, text="↺ New Match",
            font=("Arial", 11), width=11,
            bg="#333", fg="white",
            command=self.new_match
        ).grid(row=0, column=2, padx=6)

        # Keyboard shortcuts hint
        tk.Label(
            self.root,
            text="Keyboard: 1/KP1 = Player 1  |  2/KP2 = Player 2  |  0/KP0 = Undo  |  P = Pause",
            font=("Courier", 10), bg="#0d0d0d", fg="#444"
        ).pack(pady=(4, 0))

        self._bind_keys()

    def _bind_keys(self):
        """Bind regular keyboard and numpad keys."""
        # Regular number row
        self.root.bind("1", lambda e: self.handle_score(1))
        self.root.bind("2", lambda e: self.handle_score(2))
        self.root.bind("0", lambda e: self.handle_undo())
        self.root.bind("p", lambda e: self.toggle_pause())
        self.root.bind("P", lambda e: self.toggle_pause())

        # Numpad — NumLock ON  (KP_1, KP_2, KP_0)
        self.root.bind("<KP_1>", lambda e: self.handle_score(1))
        self.root.bind("<KP_2>", lambda e: self.handle_score(2))
        self.root.bind("<KP_0>", lambda e: self.handle_undo())

        # Numpad — NumLock OFF  (keys send cursor names instead)
        self.root.bind("<KP_End>",    lambda e: self.handle_score(1))   # KP 1
        self.root.bind("<KP_Down>",   lambda e: self.handle_score(2))   # KP 2
        self.root.bind("<KP_Insert>", lambda e: self.handle_undo())     # KP 0

        # Extra convenient numpad shortcuts
        self.root.bind("<KP_4>",      lambda e: self.handle_score(1))   # KP 4 → P1
        self.root.bind("<KP_Left>",   lambda e: self.handle_score(1))   # KP 4 NumLock off
        self.root.bind("<KP_6>",      lambda e: self.handle_score(2))   # KP 6 → P2
        self.root.bind("<KP_Right>",  lambda e: self.handle_score(2))   # KP 6 NumLock off
        self.root.bind("<KP_Decimal>",lambda e: self.handle_undo())     # KP . → Undo
        self.root.bind("<KP_Delete>", lambda e: self.handle_undo())     # KP . NumLock off
        self.root.bind("<KP_5>",      lambda e: self.toggle_pause())    # KP 5 → Pause
        self.root.bind("<KP_Begin>",  lambda e: self.toggle_pause())    # KP 5 NumLock off

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def handle_score(self, player: int):
        if self.paused:
            self.add_feed("Timer is paused — resume before scoring.")
            return
        self.play_sound("point")
        self.engine.score_point(player)
        self.refresh_ui()

    def handle_undo(self):
        if self.engine.undo():
            self.add_feed(f"← Undo applied  (#{self.engine.undo_count})")
        else:
            self.add_feed("Nothing to undo.")
            self.root.bell()
        self.refresh_ui()

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self._pause_offset = time.time() - self.start_time
            self.pause_btn.config(text="▶ Resume", bg="#e67e22")
            self.add_feed("Timer paused.")
        else:
            self.start_time = time.time() - self._pause_offset
            self.pause_btn.config(text="⏸ Pause", bg="#333")
            self.add_feed("Timer resumed.")

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        label = "ON" if self.sound_enabled else "OFF"
        self.sound_btn.config(text=f"🔊 Sound: {label}")

    def new_match(self):
        if messagebox.askyesno("New Match", "Start a new match? Current match will be lost."):
            self.root.destroy()
            root = tk.Tk()
            TennisProApp(root)
            root.mainloop()

    # ------------------------------------------------------------------
    # UI Refresh
    # ------------------------------------------------------------------
    def refresh_ui(self):
        s = self.engine.state

        # Server indicator
        p1_ball = "● " if s.current_server == 1 else "  "
        p2_ball = " ●" if s.current_server == 2 else "  "
        p1_color = "#f1c40f" if s.current_server == 1 else "white"
        p2_color = "#f1c40f" if s.current_server == 2 else "white"

        self.p1_label.config(text=f"{p1_ball}{self.p1_name}", fg=p1_color)
        self.p2_label.config(text=f"{self.p2_name}{p2_ball}", fg=p2_color)

        self.set_score_val.config(text=f"{s.p1_sets} - {s.p2_sets}")
        self.game_label.config(text=f"GAMES: {s.p1_games} - {s.p2_games}")
        self.score_display.config(text=self.engine.current_score_text())

        if s.is_tiebreak:
            self.status_msg.config(text="TIE-BREAK", fg="#e74c3c", bg="#1e0000")
        elif self.engine.match_finished():
            self.status_msg.config(text="MATCH OVER", fg="#00e676", bg="#001a00")
        else:
            self.status_msg.config(text="MATCH IN PROGRESS", fg="white", bg="#1e1e1e")

        self.undo_btn.config(text=f"UNDO ({self.engine.undo_count})")

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------
    def update_clock(self):
        if not self.paused:
            elapsed = int(time.time() - self.start_time)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            sec = elapsed % 60
            self.timer_label.config(text=f"{h:02d}:{m:02d}:{sec:02d}")
        self.root.after(1000, self.update_clock)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def add_feed(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.feed.insert(tk.END, f"[{ts}]  {msg}\n")
        self.feed.see(tk.END)

    def play_sound(self, sound_type: str):
        if not self.sound_enabled:
            return
        try:
            subprocess.Popen(
                ["canberra-gtk-play", "-i", SOUNDS.get(sound_type, "")],
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = TennisProApp(root)
    root.mainloop()
