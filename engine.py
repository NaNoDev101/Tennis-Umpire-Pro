"""
engine.py — Core tennis logic for Tennis Umpire Pro.

Contains three public classes:

* ``MatchState``   — pure data snapshot of the match at any instant.
* ``EventEmitter`` — lightweight, type-safe publish/subscribe bus.
* ``MatchEngine``  — all scoring, set/game/tiebreak rules, undo history.

The engine is fully independent of the UI and can be unit-tested in
isolation simply by importing this module.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Callable, Dict, List, Optional

from theme import MatchConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event names
# ---------------------------------------------------------------------------

class Event(str, Enum):
    """All events that the engine can emit.

    Using an ``Enum`` prevents silent typos in string-based event names and
    makes it easy to grep every usage.
    """
    REFRESH         = auto()
    GAME_WON        = auto()
    SET_WON         = auto()
    MATCH_FINISHED  = auto()
    TIEBREAK_START  = auto()
    CHANGE_ENDS     = auto()


# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------

class EventEmitter:
    """Minimal publish/subscribe event bus.

    Listeners are callables registered with :meth:`on`.  All listeners
    registered for a given event are invoked synchronously when
    :meth:`emit` is called.

    Example::

        emitter = EventEmitter()
        emitter.on(Event.REFRESH, my_callback)
        emitter.emit(Event.REFRESH)
    """

    def __init__(self) -> None:
        self._listeners: Dict[Event, List[Callable]] = {}

    def on(self, event: Event, callback: Callable) -> None:
        """Register *callback* to be called when *event* fires."""
        self._listeners.setdefault(event, []).append(callback)

    def emit(self, event: Event, *args: object) -> None:
        """Fire *event*, passing *args* to every registered listener."""
        for cb in self._listeners.get(event, []):
            try:
                cb(*args)
            except Exception:
                logger.exception("Error in listener for event %s", event)


# ---------------------------------------------------------------------------
# State snapshot
# ---------------------------------------------------------------------------

@dataclass
class MatchState:
    """Complete, serialisable snapshot of the match at one instant.

    All fields are plain Python scalars or simple lists so that the state
    can be cheaply serialised to a dict (via ``dataclasses.asdict``) and
    restored without ``copy.deepcopy``.

    Fields prefixed with ``_bp_`` are internal bookkeeping flags for
    break-point counting and are not displayed directly.
    """

    # ── Score ─────────────────────────────────────────────────────────────
    p1_sets:   int = 0
    p2_sets:   int = 0
    p1_games:  int = 0
    p2_games:  int = 0
    p1_points: int = 0
    p2_points: int = 0

    # ── Match flow ───────────────────────────────────────────────────────
    is_tiebreak: bool           = False
    current_server: int         = 1   # 1 or 2
    tiebreak_first_server: int  = 1   # who served the first tiebreak point

    # ── Aggregate counters ───────────────────────────────────────────────
    p1_total_points: int    = 0
    p2_total_points: int    = 0
    total_games_in_set: int = 0   # used for change-ends logic

    set_history: List[str] = field(default_factory=list)
    undo_count: int        = 0

    # ── Per-match statistics ─────────────────────────────────────────────
    p1_aces: int          = 0
    p2_aces: int          = 0
    p1_double_faults: int = 0
    p2_double_faults: int = 0

    # Break points: created = opportunities, won = converted
    p1_bp_created: int = 0
    p2_bp_created: int = 0
    p1_bp_won: int     = 0
    p2_bp_won: int     = 0

    # Internal flags — was there an active BP opportunity on the last point?
    _bp_active_p1: bool = False
    _bp_active_p2: bool = False

    # ── Helpers ───────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise to a plain dict (used for history snapshots & JSON save)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MatchState":
        """Reconstruct a ``MatchState`` from a plain dict."""
        return cls(**data)


# ---------------------------------------------------------------------------
# Match engine
# ---------------------------------------------------------------------------

_POINTS_MAP: List[str] = ["0", "15", "30", "40"]


class MatchEngine:
    """Tennis scoring engine.

    All tennis rules live here:
    * Standard game scoring (0 / 15 / 30 / 40 / Deuce / Advantage)
    * Set and match progression
    * Tiebreak with correct serve rotation
    * Break-point detection and statistics
    * Undo via lightweight serialisation-based history
    * JSON save / load with full error handling
    """

    def __init__(self, config: MatchConfig) -> None:
        self.config: MatchConfig       = config
        self.state: MatchState         = MatchState()
        self.events: EventEmitter      = EventEmitter()
        self._history: List[dict]      = []   # list of serialised snapshots
        self.sets_to_win: int          = (config.max_sets // 2) + 1

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def score_point(
        self,
        player_num: int,
        is_ace: bool = False,
        is_double_fault: bool = False,
    ) -> None:
        """Award a point to *player_num* (1 or 2) and advance match state.

        Args:
            player_num:       The player who hit the shot (1 or 2).
            is_ace:           Whether the shot was an ace.
            is_double_fault:  If ``True``, the *opponent* wins the point.
        """
        if self.is_match_over():
            return

        self._push_snapshot()

        # A double fault awards the point to the opponent.
        if is_double_fault:
            scorer = 3 - player_num
            if player_num == 1:
                self.state.p1_double_faults += 1
            else:
                self.state.p2_double_faults += 1
        else:
            scorer = player_num

        # Accumulate raw totals and optional ace stat.
        if scorer == 1:
            self.state.p1_points += 1
            self.state.p1_total_points += 1
            if is_ace:
                self.state.p1_aces += 1
        else:
            self.state.p2_points += 1
            self.state.p2_total_points += 1
            if is_ace:
                self.state.p2_aces += 1

        # Break-point bookkeeping must happen *before* game resolution.
        if not self.state.is_tiebreak:
            self._update_break_point_stats(scorer)

        # Resolve the point against tiebreak or normal game rules.
        if self.state.is_tiebreak:
            self._handle_tiebreak_point()
        else:
            self._check_game_win()

        self.events.emit(Event.REFRESH)

    def undo(self) -> bool:
        """Roll back the match state to the previous snapshot.

        Returns:
            ``True`` if a snapshot was available and the undo succeeded;
            ``False`` if there is nothing to undo.
        """
        if not self._history:
            return False

        snapshot = self._history.pop()
        self.state = MatchState.from_dict(snapshot)
        self.state.undo_count += 1
        self.events.emit(Event.REFRESH)
        return True

    def is_match_over(self) -> bool:
        """Return ``True`` when a player has won the required number of sets."""
        return (
            self.state.p1_sets >= self.sets_to_win
            or self.state.p2_sets >= self.sets_to_win
        )

    def get_score_str(self) -> str:
        """Return the current point score as a human-readable string."""
        s = self.state
        if s.is_tiebreak:
            return f"{s.p1_points}  –  {s.p2_points}"

        p1, p2 = s.p1_points, s.p2_points

        # Deuce / Advantage
        if p1 >= 3 and p2 >= 3:
            if p1 == p2:
                return "DEUCE"
            leader = self.config.p1_name if p1 > p2 else self.config.p2_name
            return f"ADV  {leader}"

        return f"{_POINTS_MAP[p1]}  –  {_POINTS_MAP[p2]}"

    def is_break_point(self) -> Optional[int]:
        """Return the player number holding a break-point opportunity, or ``None``.

        A break point exists when the receiver is at 40 or has the advantage
        (i.e. is one point away from winning the game while the server is not).
        """
        s = self.state
        if s.is_tiebreak:
            return None

        receiver = 3 - s.current_server
        r_pts = s.p1_points if receiver == 1 else s.p2_points
        s_pts = s.p2_points if receiver == 1 else s.p1_points

        # Receiver is at 40-30 or better, or has advantage at deuce
        if r_pts >= 3 and r_pts > s_pts:
            return receiver
        return None

    # ── Persistence ───────────────────────────────────────────────────────

    def save_state(self, filename: str) -> None:
        """Serialise the full match (config, state, history) to a JSON file.

        Raises:
            OSError: if the file cannot be written.
        """
        data = {
            "config":  asdict(self.config),
            "state":   self.state.to_dict(),
            "history": self._history,   # already plain dicts
        }
        with open(filename, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4)
        logger.info("Match saved to %s", filename)

    def load_state(self, filename: str) -> None:
        """Restore match state from a previously saved JSON file.

        Raises:
            FileNotFoundError: if the file does not exist.
            KeyError / ValueError: if the file is corrupt or malformed.
        """
        with open(filename, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        self.config      = MatchConfig(**data["config"])
        self.state       = MatchState.from_dict(data["state"])
        self._history    = data["history"]
        self.sets_to_win = (self.config.max_sets // 2) + 1
        logger.info("Match loaded from %s", filename)
        self.events.emit(Event.REFRESH)

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    def _push_snapshot(self) -> None:
        """Serialise current state and push onto the undo stack.

        Using ``asdict`` + a plain dict is significantly cheaper than
        ``copy.deepcopy`` for the sizes involved here.
        """
        self._history.append(self.state.to_dict())

    def _switch_server(self) -> None:
        """Toggle the current server between player 1 and player 2."""
        self.state.current_server = 3 - self.state.current_server

    # ── Break-point tracking ──────────────────────────────────────────────

    def _update_break_point_stats(self, scorer: int) -> None:
        """Track break-point opportunities and conversions.

        Called *after* the point is credited but *before* game resolution,
        so the final score reflects whether the receiver had a BP chance.

        Args:
            scorer: Player number (1 or 2) who won this point.
        """
        s        = self.state
        receiver = 3 - s.current_server
        r_pts    = s.p1_points if receiver == 1 else s.p2_points
        s_pts    = s.p2_points if receiver == 1 else s.p1_points

        # Break point: receiver is at 40 or has the advantage
        is_bp = r_pts >= 3 and r_pts >= s_pts and not (r_pts == 3 and s_pts == 3)
        # Also covers deuce-side: r≥3, s≥3, r>s
        is_bp = is_bp or (r_pts >= 3 and s_pts >= 3 and r_pts > s_pts)

        if is_bp:
            # Register a *new* break-point opportunity (guard against
            # counting the same deuce-advantage cycle twice).
            if receiver == 1 and not s._bp_active_p1:
                s.p1_bp_created += 1
                s._bp_active_p1 = True
            elif receiver == 2 and not s._bp_active_p2:
                s.p2_bp_created += 1
                s._bp_active_p2 = True

            # If the receiver wins the point, the break is converted.
            if scorer == receiver:
                if receiver == 1:
                    s.p1_bp_won += 1
                    s._bp_active_p1 = False
                else:
                    s.p2_bp_won += 1
                    s._bp_active_p2 = False
        else:
            # Score returned to non-BP territory; reset flags.
            s._bp_active_p1 = False
            s._bp_active_p2 = False

    # ── Game resolution ───────────────────────────────────────────────────

    def _check_game_win(self) -> None:
        """Award a game if either player has reached the winning threshold."""
        p1, p2 = self.state.p1_points, self.state.p2_points
        if p1 >= 4 and p1 - p2 >= 2:
            self._win_game(1)
        elif p2 >= 4 and p2 - p1 >= 2:
            self._win_game(2)

    def _win_game(self, player: int) -> None:
        """Credit *player* with a game and advance match flow."""
        s = self.state
        s.p1_points = 0
        s.p2_points = 0
        s._bp_active_p1 = False
        s._bp_active_p2 = False

        if player == 1:
            s.p1_games += 1
        else:
            s.p2_games += 1

        s.total_games_in_set += 1
        self._switch_server()

        # Change ends every odd game within a set.
        if s.total_games_in_set % 2 == 1:
            self.events.emit(Event.CHANGE_ENDS)

        self._check_set()
        self.events.emit(Event.GAME_WON, player)

    # ── Set resolution ────────────────────────────────────────────────────

    def _check_set(self) -> None:
        """Determine whether the current set has been won or a tiebreak begins."""
        s     = self.state
        limit = self.config.tiebreak_at
        p1g, p2g = s.p1_games, s.p2_games

        if (p1g >= limit and p1g - p2g >= 2) or p1g == limit + 1:
            self._win_set(1)
        elif (p2g >= limit and p2g - p1g >= 2) or p2g == limit + 1:
            self._win_set(2)
        elif p1g == limit and p2g == limit:
            # Both players reached the tiebreak threshold.
            s.is_tiebreak = True
            s.tiebreak_first_server = s.current_server
            self.events.emit(Event.TIEBREAK_START)

    def _win_set(self, player: int) -> None:
        """Credit *player* with a set and reset per-set counters."""
        s = self.state
        s.set_history.append(f"{s.p1_games}-{s.p2_games}")

        if player == 1:
            s.p1_sets += 1
        else:
            s.p2_sets += 1

        s.p1_games          = 0
        s.p2_games          = 0
        s.is_tiebreak       = False
        s.total_games_in_set = 0

        # Players change ends between sets.
        self.events.emit(Event.CHANGE_ENDS)
        self.events.emit(Event.SET_WON, player)

        if self.is_match_over():
            self.events.emit(Event.MATCH_FINISHED, player)

    # ── Tiebreak logic ────────────────────────────────────────────────────

    def _handle_tiebreak_point(self) -> None:
        """Apply tiebreak-specific serve rotation and check for tiebreak win.

        Tiebreak serve rules (standard ATP/WTA):
        * The player who was *receiving* at the start serves the **first**
          point.
        * After point 1 the server changes every **2** points.
        * Players change ends every **6** points.
        * Tiebreak won at 7 points with a 2-point lead (or higher with 2-pt gap).
        """
        s = self.state
        total_tb_points = s.p1_points + s.p2_points  # AFTER crediting this point

        # Serve rotation: change after point 1, then every 2 points.
        if total_tb_points == 1 or (total_tb_points > 1 and total_tb_points % 2 == 1):
            self._switch_server()

        # Change ends every 6 tiebreak points.
        if total_tb_points > 0 and total_tb_points % 6 == 0:
            self.events.emit(Event.CHANGE_ENDS)

        # Tiebreak win condition.
        p1, p2 = s.p1_points, s.p2_points
        if p1 >= 7 and p1 - p2 >= 2:
            self._win_game(1)
        elif p2 >= 7 and p2 - p1 >= 2:
            self._win_game(2)
