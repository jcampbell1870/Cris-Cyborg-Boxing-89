"""Tests for the boxing gameplay engine."""

from __future__ import annotations

import random

from criscyborg.game.ai import BoxerAI
from criscyborg.game.engine import (
    KNOCKOUT_SECONDS,
    ROUND_DURATION,
    TOTAL_ROUNDS,
    Action,
    Boxer,
    BoxingMatch,
    GameState,
)
from criscyborg.models import Difficulty


def make_match(seed: int = 3) -> BoxingMatch:
    match = BoxingMatch(
        boxer1=Boxer.from_difficulty("Challenger", Difficulty.MEDIUM),
        boxer2=Boxer.from_difficulty("Cris Cyborg", Difficulty.EXPERT),
        rng=random.Random(seed),
    )
    match.start()
    return match


def test_match_starts_with_three_full_rounds() -> None:
    match = make_match()
    assert match.state is GameState.IN_MATCH
    assert match.total_rounds == TOTAL_ROUNDS
    assert match.round_time_remaining == ROUND_DURATION
    assert match.boxer1.current_health == 100.0


def test_punch_damages_the_opponent_and_scores() -> None:
    match = make_match()
    match.apply_action(match.boxer1, Action.LEFT_PUNCH)
    assert match.boxer2.current_health < 100.0
    assert match.boxer1.score == 10


def test_special_scores_more_than_a_punch() -> None:
    match = make_match()
    match.apply_action(match.boxer1, Action.SPECIAL)
    assert match.boxer1.score == 25


def test_dodge_reduces_incoming_damage() -> None:
    dodged = make_match()
    dodged.apply_action(dodged.boxer2, Action.DODGE)
    dodged.apply_action(dodged.boxer1, Action.LEFT_PUNCH)
    dodged_damage = 100.0 - dodged.boxer2.current_health

    clean = make_match()
    clean.apply_action(clean.boxer1, Action.LEFT_PUNCH)
    clean_damage = 100.0 - clean.boxer2.current_health

    assert dodged_damage < clean_damage


def test_knockdown_when_health_drops_below_thirty_percent() -> None:
    match = make_match()
    match.boxer2.take_damage(75.0)
    assert match.boxer2.is_knocked_down
    assert not match.boxer2.is_knocked_out


def test_knockout_ends_the_match() -> None:
    match = make_match()
    match.boxer2.take_damage(200.0)
    match.tick(0.016)
    assert match.is_over
    assert match.winner is match.boxer1
    assert match.boxer2.knockdown_timer <= KNOCKOUT_SECONDS


def test_knocked_down_boxer_cannot_act() -> None:
    match = make_match()
    match.boxer1.is_knocked_down = True
    match.apply_action(match.boxer1, Action.LEFT_PUNCH)
    assert match.boxer1.score == 0


def test_stamina_limits_spam_and_regenerates() -> None:
    match = make_match()
    match.boxer1.stamina = 3.0
    match.apply_action(match.boxer1, Action.LEFT_PUNCH)
    assert match.boxer1.score == 0
    match.boxer1.tick(1.0)
    assert match.boxer1.stamina > 3.0


def test_three_rounds_then_decision_on_points() -> None:
    match = make_match()
    match.boxer1.score = 500
    for _ in range(TOTAL_ROUNDS):
        match.tick(ROUND_DURATION)
    assert match.is_over
    assert match.winner is match.boxer1


def test_decision_falls_back_to_health_on_a_score_tie() -> None:
    match = make_match()
    match.boxer1.score = match.boxer2.score = 100
    match.boxer2.current_health = 40.0
    assert match.determine_winner() is match.boxer1


def test_ai_drives_a_bout_to_completion() -> None:
    rng = random.Random(11)
    match = make_match(seed=11)
    ai1 = BoxerAI(match.boxer1, rng)
    ai2 = BoxerAI(match.boxer2, rng)
    for _ in range(2000):
        if match.is_over:
            break
        ai1.act(match)
        ai2.act(match)
        match.tick(0.5)
    assert match.is_over
    assert match.winner is not None


def test_snapshot_is_serializable() -> None:
    match = make_match()
    snapshot = match.snapshot()
    assert snapshot["totalRounds"] == 3
    assert snapshot["boxer1"]["name"] == "Challenger"
    assert "health" in snapshot["boxer2"]
