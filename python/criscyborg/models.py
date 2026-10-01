"""Domain models for Cris Cyborg Boxing 89 (Python 3 rewrite)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


def new_id(prefix: str, length: int = 8) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:length]}"


def now_ts() -> float:
    return time.time()


class MatchState(str, Enum):
    WAITING_FOR_OPPONENT = "WaitingForOpponent"
    PENDING = "Pending"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class TournamentStatus(str, Enum):
    REGISTRATION = "Registration"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class RewardStatus(str, Enum):
    PENDING = "Pending"
    #: A signed vault claim was issued but has not been submitted on-chain yet.
    ISSUED = "Issued"
    COMPLETED = "Completed"
    FAILED = "Failed"


class Difficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    EXPERT = "Expert"


@dataclass
class ChampionshipBelt:
    tournament_id: str
    tournament_name: str
    awarded_at: float = field(default_factory=now_ts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tournamentId": self.tournament_id,
            "tournamentName": self.tournament_name,
            "awardedAt": self.awarded_at,
        }


@dataclass
class Player:
    """A wallet-identified player. Identity is the MetaMask address."""

    address: str
    username: str
    skill_level: int = 5
    wins: int = 0
    losses: int = 0
    championship_belts: list[ChampionshipBelt] = field(default_factory=list)
    created_at: float = field(default_factory=now_ts)
    last_login_at: float = field(default_factory=now_ts)
    is_active: bool = True

    @property
    def elo(self) -> int:
        return 1000 + (self.wins * 32) - (self.losses * 16)

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "username": self.username,
            "skillLevel": self.skill_level,
            "wins": self.wins,
            "losses": self.losses,
            "elo": self.elo,
            "championshipBelts": [belt.to_dict() for belt in self.championship_belts],
        }


@dataclass
class Match:
    """A one-vs-one bout, either standalone or a tournament bracket match."""

    id: str
    player1: str
    player2: str | None = None
    state: MatchState = MatchState.WAITING_FOR_OPPONENT
    winner: str | None = None
    player1_score: int = 0
    player2_score: int = 0
    rounds_completed: int = 0
    reward_amount: Decimal = Decimal(0)
    tournament_id: str | None = None
    round_number: int = 0
    created_at: float = field(default_factory=now_ts)
    started_at: float | None = None
    ended_at: float | None = None

    def seats(self) -> list[str]:
        return [p for p in (self.player1, self.player2) if p]

    def has_seat(self, address: str) -> bool:
        return address.lower() in {p.lower() for p in self.seats()}

    def opponent_of(self, address: str) -> str | None:
        low = address.lower()
        if self.player1 and self.player1.lower() == low:
            return self.player2
        if self.player2 and self.player2.lower() == low:
            return self.player1
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "player1": self.player1,
            "player2": self.player2,
            "state": self.state.value,
            "winner": self.winner,
            "player1Score": self.player1_score,
            "player2Score": self.player2_score,
            "roundsCompleted": self.rounds_completed,
            "rewardAmount": str(self.reward_amount),
            "tournamentId": self.tournament_id,
            "round": self.round_number,
            "createdAt": self.created_at,
            "startedAt": self.started_at,
            "endedAt": self.ended_at,
        }


@dataclass
class Tournament:
    """A GG Poker style eight-max sit-and-go bracket."""

    id: str
    name: str
    host: str
    seat_limit: int = 8
    status: TournamentStatus = TournamentStatus.REGISTRATION
    entrants: list[str] = field(default_factory=list)
    rounds: list[list[str]] = field(default_factory=list)  # match ids per round
    champion: str | None = None
    championship_belt: ChampionshipBelt | None = None
    prize_pool: Decimal = Decimal(0)
    created_at: float = field(default_factory=now_ts)
    started_at: float | None = None
    ended_at: float | None = None

    @property
    def seats_available(self) -> int:
        return max(0, self.seat_limit - len(self.entrants))

    def is_entrant(self, address: str) -> bool:
        return address.lower() in {e.lower() for e in self.entrants}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "seatLimit": self.seat_limit,
            "seatsAvailable": self.seats_available,
            "status": self.status.value,
            "entrants": list(self.entrants),
            "rounds": [list(r) for r in self.rounds],
            "champion": self.champion,
            "championshipBelt": (
                self.championship_belt.to_dict() if self.championship_belt else None
            ),
            "prizePool": str(self.prize_pool),
            "createdAt": self.created_at,
            "startedAt": self.started_at,
            "endedAt": self.ended_at,
        }


@dataclass
class Reward:
    """An Arcade1870 vault claim issued to a player.

    The backend never transfers ARC: it signs an EIP-712 ``Claim`` that the
    player submits to the shared ``Arcade1870RewardVault`` themselves, paying
    their own gas.
    """

    id: str
    recipient: str
    amount: Decimal
    amount_wei: int
    nonce: int
    deadline: int
    signature: str
    vault_address: str
    token_address: str
    chain_id: int
    token_symbol: str
    token_decimals: int
    game_id: str
    status: RewardStatus = RewardStatus.ISSUED
    transaction_hash: str | None = None
    created_at: float = field(default_factory=now_ts)
    completed_at: float | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "recipient": self.recipient,
            "amount": str(self.amount),
            "amountWei": str(self.amount_wei),
            "nonce": str(self.nonce),
            "deadline": self.deadline,
            "signature": self.signature,
            "vaultAddress": self.vault_address,
            "tokenAddress": self.token_address,
            "chainId": self.chain_id,
            "tokenSymbol": self.token_symbol,
            "tokenDecimals": self.token_decimals,
            "gameId": self.game_id,
            "status": self.status.value,
            "transactionHash": self.transaction_hash,
            "createdAt": self.created_at,
            "completedAt": self.completed_at,
        }
