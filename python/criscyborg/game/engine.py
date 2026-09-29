"""Boxing gameplay engine - the Python 3 rewrite of the Unreal C++ gameplay.

Ports ``ABoxer`` (``Boxer.cpp``) and ``ACrisCyborgBoxingGameMode``
(``CrisCyborgBoxingGameMode.cpp``): three 120 second rounds, KO and
points victories, punches, special attacks and dodges.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..models import Difficulty

MAX_HEALTH = 100.0
ROUND_DURATION = 120.0
TOTAL_ROUNDS = 3
KNOCKOUT_SECONDS = 3.0
KNOCKDOWN_SECONDS = 1.0
KNOCKDOWN_HEALTH_RATIO = 0.3
PUNCH_STAMINA_COST = 4
SPECIAL_STAMINA_COST = 12
DODGE_STAMINA_COST = 6
STAMINA_REGEN_PER_SECOND = 6.0

DIFFICULTY_STATS: dict[Difficulty, dict[str, int]] = {
    Difficulty.EASY: {"speed": 3, "power": 3, "defense": 3},
    Difficulty.MEDIUM: {"speed": 5, "power": 5, "defense": 5},
    Difficulty.HARD: {"speed": 7, "power": 7, "defense": 7},
    Difficulty.EXPERT: {"speed": 9, "power": 9, "defense": 9},
}


class GameState(str, Enum):
    MAIN_MENU = "MainMenu"
    IN_MATCH = "InMatch"
    ROUND_END = "RoundEnd"
    MATCH_END = "MatchEnd"


class Action(str, Enum):
    LEFT_PUNCH = "left_punch"
    RIGHT_PUNCH = "right_punch"
    SPECIAL = "special"
    DODGE = "dodge"
    IDLE = "idle"


@dataclass
class Boxer:
    """A single fighter's stats and per-round state."""

    name: str
    speed: int = 5
    power: int = 5
    defense: int = 5
    difficulty: Difficulty = Difficulty.MEDIUM
    max_health: float = MAX_HEALTH
    current_health: float = MAX_HEALTH
    stamina: float = 100.0
    score: int = 0
    rounds_won: int = 0
    is_knocked_down: bool = False
    is_dodging: bool = False
    knockdown_timer: float = 0.0
    dodge_timer: float = 0.0

    @classmethod
    def from_difficulty(cls, name: str, difficulty: Difficulty) -> "Boxer":
        stats = DIFFICULTY_STATS[difficulty]
        return cls(name=name, difficulty=difficulty, **stats)

    @property
    def is_knocked_out(self) -> bool:
        return self.current_health <= 0.0

    def tick(self, delta_time: float) -> None:
        if self.is_knocked_down:
            self.knockdown_timer -= delta_time
            if self.knockdown_timer <= 0.0:
                self.is_knocked_down = False
                self.knockdown_timer = 0.0
        if self.is_dodging:
            self.dodge_timer -= delta_time
            if self.dodge_timer <= 0.0:
                self.is_dodging = False
                self.dodge_timer = 0.0
        self.stamina = min(100.0, self.stamina + STAMINA_REGEN_PER_SECOND * delta_time)

    def take_damage(self, amount: float) -> None:
        if amount <= 0:
            return
        self.current_health -= amount
        if self.current_health <= 0.0:
            self.current_health = 0.0
            self.is_knocked_down = True
            self.knockdown_timer = KNOCKOUT_SECONDS
        elif self.current_health < self.max_health * KNOCKDOWN_HEALTH_RATIO:
            self.is_knocked_down = True
            self.knockdown_timer = KNOCKDOWN_SECONDS

    def punch_damage(self, rng: random.Random) -> float:
        return 5.0 + (self.power * 2) + rng.uniform(-2.0, 2.0)

    def special_damage(self, rng: random.Random) -> float:
        return (5.0 + (self.power * 2)) * 1.5 + rng.uniform(-2.0, 2.0)

    def reset_round(self) -> None:
        self.current_health = self.max_health
        self.stamina = 100.0
        self.is_knocked_down = False
        self.is_dodging = False
        self.knockdown_timer = 0.0
        self.dodge_timer = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "health": round(self.current_health, 2),
            "maxHealth": self.max_health,
            "stamina": round(self.stamina, 2),
            "score": self.score,
            "roundsWon": self.rounds_won,
            "isKnockedDown": self.is_knocked_down,
            "isDodging": self.is_dodging,
            "power": self.power,
            "speed": self.speed,
            "defense": self.defense,
            "difficulty": self.difficulty.value,
        }


@dataclass
class BoxingMatch:
    """Authoritative three round bout between two boxers."""

    boxer1: Boxer
    boxer2: Boxer
    round_duration: float = ROUND_DURATION
    total_rounds: int = TOTAL_ROUNDS
    current_round: int = 1
    round_time_remaining: float = ROUND_DURATION
    state: GameState = GameState.MAIN_MENU
    winner: Boxer | None = None
    rng: random.Random = field(default_factory=random.Random)
    events: list[str] = field(default_factory=list)

    def start(self) -> None:
        self.current_round = 1
        self.round_time_remaining = self.round_duration
        self.winner = None
        self.boxer1.reset_round()
        self.boxer2.reset_round()
        self.boxer1.score = 0
        self.boxer2.score = 0
        self.boxer1.rounds_won = 0
        self.boxer2.rounds_won = 0
        self.state = GameState.IN_MATCH
        self.events.append("Match started")

    def opponent(self, boxer: Boxer) -> Boxer:
        return self.boxer2 if boxer is self.boxer1 else self.boxer1

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def apply_action(self, boxer: Boxer, action: Action) -> None:
        if self.state is not GameState.IN_MATCH or boxer.is_knocked_down:
            return

        defender = self.opponent(boxer)

        if action in (Action.LEFT_PUNCH, Action.RIGHT_PUNCH):
            if boxer.stamina < PUNCH_STAMINA_COST:
                return
            boxer.stamina -= PUNCH_STAMINA_COST
            boxer.score += 10
            self._land(boxer, defender, boxer.punch_damage(self.rng))
        elif action is Action.SPECIAL:
            if boxer.stamina < SPECIAL_STAMINA_COST:
                return
            boxer.stamina -= SPECIAL_STAMINA_COST
            boxer.score += 25
            self._land(boxer, defender, boxer.special_damage(self.rng))
        elif action is Action.DODGE:
            if boxer.stamina < DODGE_STAMINA_COST:
                return
            boxer.stamina -= DODGE_STAMINA_COST
            boxer.is_dodging = True
            boxer.dodge_timer = 0.4

    def _land(self, attacker: Boxer, defender: Boxer, damage: float) -> None:
        if defender.is_dodging:
            # A successful dodge scales the hit down by the defender's
            # defense stat instead of negating scoring entirely.
            damage *= max(0.0, 1.0 - (defender.defense / 10.0))
            self.events.append(f"{defender.name} dodged {attacker.name}")
        damage = max(0.0, damage)
        defender.take_damage(damage)
        if defender.is_knocked_out:
            self.events.append(f"{attacker.name} knocked out {defender.name}")

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def tick(self, delta_time: float) -> None:
        if self.state is not GameState.IN_MATCH:
            return
        self.boxer1.tick(delta_time)
        self.boxer2.tick(delta_time)
        self._check_win_conditions()
        if self.state is not GameState.IN_MATCH:
            return
        self.round_time_remaining -= delta_time
        if self.round_time_remaining <= 0.0:
            self.end_round()

    def _check_win_conditions(self) -> None:
        if self.boxer1.is_knocked_out:
            self._finish(self.boxer2, f"{self.boxer2.name} wins by KO")
        elif self.boxer2.is_knocked_out:
            self._finish(self.boxer1, f"{self.boxer1.name} wins by KO")

    def end_round(self) -> None:
        self.state = GameState.ROUND_END
        round_winner = self._round_leader()
        if round_winner is not None:
            round_winner.rounds_won += 1
        self.events.append(f"Round {self.current_round} complete")

        if self.current_round < self.total_rounds:
            self.current_round += 1
            self.round_time_remaining = self.round_duration
            self.boxer1.reset_round()
            self.boxer2.reset_round()
            self.state = GameState.IN_MATCH
        else:
            self._finish(self.determine_winner(), "Match decided on points")

    def _round_leader(self) -> Boxer | None:
        if self.boxer1.current_health > self.boxer2.current_health:
            return self.boxer1
        if self.boxer2.current_health > self.boxer1.current_health:
            return self.boxer2
        if self.boxer1.score > self.boxer2.score:
            return self.boxer1
        if self.boxer2.score > self.boxer1.score:
            return self.boxer2
        return None

    def determine_winner(self) -> Boxer:
        """Score first, then health, matching the original game mode."""
        if self.boxer1.score > self.boxer2.score:
            return self.boxer1
        if self.boxer2.score > self.boxer1.score:
            return self.boxer2
        if self.boxer1.current_health > self.boxer2.current_health:
            return self.boxer1
        return self.boxer2

    def _finish(self, winner: Boxer, reason: str) -> None:
        self.winner = winner
        self.state = GameState.MATCH_END
        self.events.append(reason)

    @property
    def is_over(self) -> bool:
        return self.state is GameState.MATCH_END

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "round": self.current_round,
            "totalRounds": self.total_rounds,
            "roundTimeRemaining": round(max(0.0, self.round_time_remaining), 2),
            "boxer1": self.boxer1.to_dict(),
            "boxer2": self.boxer2.to_dict(),
            "winner": self.winner.name if self.winner else None,
            "events": self.events[-10:],
        }
