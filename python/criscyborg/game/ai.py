"""Simple AI opponent used for offline practice bouts."""

from __future__ import annotations

import random

from ..models import Difficulty
from .engine import Action, Boxer, BoxingMatch

#: Probability weights per difficulty: (punch, special, dodge, idle).
_POLICY: dict[Difficulty, tuple[float, float, float, float]] = {
    Difficulty.EASY: (0.35, 0.05, 0.10, 0.50),
    Difficulty.MEDIUM: (0.45, 0.12, 0.18, 0.25),
    Difficulty.HARD: (0.50, 0.20, 0.22, 0.08),
    Difficulty.EXPERT: (0.52, 0.28, 0.18, 0.02),
}


class BoxerAI:
    """Chooses actions for a computer controlled boxer."""

    def __init__(self, boxer: Boxer, rng: random.Random | None = None) -> None:
        self.boxer = boxer
        self.rng = rng or random.Random()

    def choose_action(self, match: BoxingMatch) -> Action:
        if self.boxer.is_knocked_down:
            return Action.IDLE

        punch, special, dodge, idle = _POLICY[self.boxer.difficulty]
        opponent = match.opponent(self.boxer)

        # Press the advantage when the opponent is hurt, cover up when low.
        if opponent.current_health < opponent.max_health * 0.35:
            special += 0.15
            idle = max(0.0, idle - 0.15)
        if self.boxer.current_health < self.boxer.max_health * 0.35:
            dodge += 0.2
            punch = max(0.0, punch - 0.2)

        choice = self.rng.choices(
            [Action.LEFT_PUNCH, Action.SPECIAL, Action.DODGE, Action.IDLE],
            weights=[punch, special, dodge, idle],
            k=1,
        )[0]
        if choice is Action.LEFT_PUNCH and self.rng.random() < 0.5:
            return Action.RIGHT_PUNCH
        return choice

    def act(self, match: BoxingMatch) -> Action:
        action = self.choose_action(match)
        if action is not Action.IDLE:
            match.apply_action(self.boxer, action)
        return action
