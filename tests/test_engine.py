"""
tests/test_engine.py — Unit tests for MatchEngine (no UI required).

Run with::

    cd tennis_umpire_pro
    python -m pytest tests/
"""

from __future__ import annotations

import pytest

from engine import Event, MatchEngine, MatchState
from theme import MatchConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_engine(**kwargs) -> MatchEngine:
    """Return a MatchEngine with sensible test defaults."""
    config = MatchConfig(
        p1_name="Alice",
        p2_name="Bob",
        max_sets=kwargs.pop("max_sets", 3),
        tiebreak_at=kwargs.pop("tiebreak_at", 6),
        sound_enabled=False,
    )
    return MatchEngine(config)


def score_n(engine: MatchEngine, player: int, n: int) -> None:
    """Score *n* plain points for *player*."""
    for _ in range(n):
        engine.score_point(player)


def win_game(engine: MatchEngine, player: int) -> None:
    """Win a full game for *player* from 0-0."""
    score_n(engine, player, 4)


def win_set(engine: MatchEngine, player: int, games: int = 6) -> None:
    """Win *games* games in a row for *player* to take a set."""
    for _ in range(games):
        win_game(engine, player)


# ---------------------------------------------------------------------------
# Scoring fundamentals
# ---------------------------------------------------------------------------

class TestPointScoring:
    def test_points_increment(self):
        e = make_engine()
        e.score_point(1)
        assert e.state.p1_points == 1

    def test_score_str_0_0(self):
        e = make_engine()
        assert e.get_score_str() == "0  –  0"

    def test_score_str_15_0(self):
        e = make_engine()
        e.score_point(1)
        assert e.get_score_str() == "15  –  0"

    def test_score_str_40_30(self):
        e = make_engine()
        score_n(e, 1, 3)
        score_n(e, 2, 2)
        assert e.get_score_str() == "40  –  30"

    def test_deuce(self):
        e = make_engine()
        score_n(e, 1, 3)
        score_n(e, 2, 3)
        assert e.get_score_str() == "DEUCE"

    def test_advantage_p1(self):
        e = make_engine()
        score_n(e, 1, 3)
        score_n(e, 2, 3)
        e.score_point(1)
        assert "ADV" in e.get_score_str() and "Alice" in e.get_score_str()

    def test_advantage_p2(self):
        e = make_engine()
        score_n(e, 1, 3)
        score_n(e, 2, 3)
        e.score_point(2)
        assert "ADV" in e.get_score_str() and "Bob" in e.get_score_str()

    def test_ace_increments_stat(self):
        e = make_engine()
        e.score_point(1, is_ace=True)
        assert e.state.p1_aces == 1

    def test_double_fault_awards_opponent(self):
        e = make_engine()
        e.score_point(1, is_double_fault=True)
        assert e.state.p2_points == 1
        assert e.state.p1_double_faults == 1


# ---------------------------------------------------------------------------
# Game progression
# ---------------------------------------------------------------------------

class TestGameProgression:
    def test_game_win_resets_points(self):
        e = make_engine()
        win_game(e, 1)
        assert e.state.p1_points == 0
        assert e.state.p2_points == 0

    def test_game_increments_game_count(self):
        e = make_engine()
        win_game(e, 1)
        assert e.state.p1_games == 1

    def test_server_switches_after_game(self):
        e = make_engine()
        initial_server = e.state.current_server
        win_game(e, 1)
        assert e.state.current_server != initial_server

    def test_deuce_needs_two_point_lead(self):
        e = make_engine()
        score_n(e, 1, 3)
        score_n(e, 2, 3)
        # At deuce, P1 wins one → advantage
        e.score_point(1)
        # Still no game won
        assert e.state.p1_games == 0
        # Back to deuce
        e.score_point(2)
        assert e.get_score_str() == "DEUCE"
        # P1 wins two in a row → game
        e.score_point(1)
        e.score_point(1)
        assert e.state.p1_games == 1


# ---------------------------------------------------------------------------
# Set progression
# ---------------------------------------------------------------------------

class TestSetProgression:
    def test_win_set_6_0(self):
        e = make_engine()
        win_set(e, 1, 6)
        assert e.state.p1_sets == 1
        assert e.state.p1_games == 0   # reset after set

    def test_set_history_recorded(self):
        e = make_engine()
        win_set(e, 1, 6)
        assert e.state.set_history == ["6-0"]

    def test_tiebreak_triggered_at_6_6(self):
        e = make_engine()
        events_fired = []
        e.events.on(Event.TIEBREAK_START, lambda: events_fired.append("tb"))
        for _ in range(6):
            win_game(e, 1)
            win_game(e, 2)
        assert "tb" in events_fired
        assert e.state.is_tiebreak is True

    def test_win_set_7_5(self):
        """Player who reaches 7-5 wins without tiebreak."""
        e = make_engine()
        for _ in range(5):
            win_game(e, 1)
            win_game(e, 2)
        # 5-5; P1 wins 2 more
        win_game(e, 1)
        win_game(e, 1)
        assert e.state.p1_sets == 1

    def test_match_over_best_of_3(self):
        e = make_engine(max_sets=3)
        win_set(e, 1, 6)
        win_set(e, 1, 6)
        assert e.is_match_over()


# ---------------------------------------------------------------------------
# Tiebreak
# ---------------------------------------------------------------------------

class TestTiebreak:
    def _get_to_tiebreak(self) -> MatchEngine:
        e = make_engine()
        for _ in range(6):
            win_game(e, 1)
            win_game(e, 2)
        return e

    def test_tiebreak_score_str(self):
        e = self._get_to_tiebreak()
        assert e.state.is_tiebreak
        e.score_point(1)
        assert e.get_score_str() == "1  –  0"

    def test_tiebreak_win_at_7(self):
        e = self._get_to_tiebreak()
        score_n(e, 1, 7)
        assert e.state.is_tiebreak is False   # tiebreak game resolved

    def test_tiebreak_needs_2_lead(self):
        e = self._get_to_tiebreak()
        score_n(e, 1, 7)
        score_n(e, 2, 6)   # 7-6 → not enough
        # Still in tiebreak territory (game should need 9-7 etc.)
        # At 7-6 the game is won by P1; verify:
        # Actually 7-6 IS won (7 >= 7, 7-6 = 1 which is NOT >= 2)
        # So we need 8-6 scenario:
        e2 = self._get_to_tiebreak()
        score_n(e2, 1, 6)
        score_n(e2, 2, 6)   # 6-6 in tiebreak
        score_n(e2, 1, 1)   # 7-6 — still tied at game lead check
        assert e2.state.is_tiebreak is True   # not over yet (only 1 ahead)
        score_n(e2, 1, 1)   # 8-6 — wins
        assert e2.state.is_tiebreak is False


# ---------------------------------------------------------------------------
# Break-point detection
# ---------------------------------------------------------------------------

class TestBreakPoint:
    def test_bp_when_receiver_at_40_30(self):
        e = make_engine()
        # Player 1 serves first; receiver is P2
        # Give P2 three points, P1 two → 30-40 (server 30, receiver 40)
        score_n(e, 1, 2)
        score_n(e, 2, 3)
        assert e.is_break_point() == 2

    def test_no_bp_at_deuce(self):
        e = make_engine()
        score_n(e, 1, 3)
        score_n(e, 2, 3)
        # At deuce (3-3) nobody has the advantage yet
        assert e.is_break_point() is None

    def test_bp_at_advantage_receiver(self):
        e = make_engine()
        score_n(e, 1, 3)
        score_n(e, 2, 3)
        e.score_point(2)   # P2 advantage (receiver has advantage)
        assert e.is_break_point() == 2

    def test_no_bp_in_tiebreak(self):
        e = make_engine()
        for _ in range(6):
            win_game(e, 1)
            win_game(e, 2)
        assert e.is_break_point() is None


# ---------------------------------------------------------------------------
# Undo
# ---------------------------------------------------------------------------

class TestUndo:
    def test_undo_reverts_point(self):
        e = make_engine()
        e.score_point(1)
        e.undo()
        assert e.state.p1_points == 0

    def test_undo_reverts_game(self):
        e = make_engine()
        win_game(e, 1)
        e.undo()
        assert e.state.p1_games == 0

    def test_undo_when_empty_returns_false(self):
        e = make_engine()
        assert e.undo() is False

    def test_undo_count_increments(self):
        e = make_engine()
        e.score_point(1)
        e.undo()
        assert e.state.undo_count == 1


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------

class TestSerialisationRoundTrip:
    def test_state_dict_roundtrip(self):
        e = make_engine()
        win_game(e, 1)
        score_n(e, 2, 2)
        d = e.state.to_dict()
        restored = MatchState.from_dict(d)
        assert restored.p1_games == e.state.p1_games
        assert restored.p2_points == e.state.p2_points

    def test_save_load(self, tmp_path):
        e = make_engine()
        win_game(e, 1)
        path = str(tmp_path / "match.json")
        e.save_state(path)

        e2 = make_engine()
        e2.load_state(path)
        assert e2.state.p1_games == 1
