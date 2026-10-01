"""Online competition service: GG Poker style lobby, tables and sit-and-gos.

Two formats are supported, both wallet-identified:

* **Heads-up (one vs one)** - a player opens a table, a second player takes the
  open seat and the bout starts immediately.
* **Eight-max sit-and-go tournaments** - a player registers a tournament, up to
  eight entrants take a seat, and the bracket auto-starts the moment the table
  is full (three knockout rounds: quarter-final, semi-final, final).

Winners of a completed bout receive an Arcade1870 vault claim through
:class:`~criscyborg.rewards.RewardIssuer` - the same flat payout system used
by Crypto Hockey, paid from the same shared treasury vault.
"""

from __future__ import annotations

import random
import threading
from decimal import Decimal
from typing import Any

from .models import (
    ChampionshipBelt,
    Match,
    MatchState,
    Player,
    Reward,
    Tournament,
    TournamentStatus,
    new_id,
    now_ts,
)
from .rewards import RewardError, RewardIssuer
from .wallet import display_name, normalize_address

SEAT_LIMIT = 8
LOBBY_MATCH_LIMIT = 20
LOBBY_TOURNAMENT_LIMIT = 10


class LobbyError(Exception):
    """Raised when a lobby action is not permitted."""


class OnlineCompetitionService:
    """Thread-safe in-memory lobby for heads-up matches and tournaments."""

    def __init__(
        self,
        reward_issuer: RewardIssuer | None = None,
        seat_limit: int = SEAT_LIMIT,
        rng: random.Random | None = None,
    ) -> None:
        self.reward_issuer = reward_issuer
        self.seat_limit = seat_limit
        self._rng = rng or random.Random()
        self._lock = threading.RLock()
        self._players: dict[str, Player] = {}
        self._matches: dict[str, Match] = {}
        self._tournaments: dict[str, Tournament] = {}
        self._queue: list[str] = []

    # ------------------------------------------------------------------
    # Players
    # ------------------------------------------------------------------
    def upsert_player(self, address: str, username: str | None = None) -> Player:
        address = normalize_address(address)
        with self._lock:
            player = self._players.get(address.lower())
            if player is None:
                player = Player(
                    address=address, username=display_name(address, username)
                )
                self._players[address.lower()] = player
            else:
                if username:
                    player.username = display_name(address, username)
                player.last_login_at = now_ts()
            return player

    def get_player(self, address: str) -> Player | None:
        return self._players.get((address or "").lower())

    def _require_player(self, address: str) -> Player:
        player = self.get_player(address)
        if player is None:
            raise LobbyError("Player is not signed in.")
        return player

    def leaderboard(self, limit: int = 20) -> list[Player]:
        return sorted(
            self._players.values(), key=lambda p: (p.elo, p.wins), reverse=True
        )[:limit]

    # ------------------------------------------------------------------
    # Heads-up (one vs one)
    # ------------------------------------------------------------------
    def create_heads_up_match(self, host: str) -> Match:
        host = normalize_address(host)
        self._require_player(host)
        with self._lock:
            match = Match(id=new_id("hu", 11), player1=host)
            self._matches[match.id] = match
            return match

    def join_heads_up_match(self, match_id: str, address: str) -> Match:
        address = normalize_address(address)
        self._require_player(address)
        with self._lock:
            match = self._get_match(match_id)
            if match.tournament_id is not None:
                raise LobbyError("Tournament matches cannot be joined from the lobby.")
            if match.state is not MatchState.WAITING_FOR_OPPONENT:
                raise LobbyError("That table is no longer open.")
            if match.has_seat(address):
                raise LobbyError("You cannot join your own table.")
            match.player2 = address
            match.state = MatchState.IN_PROGRESS
            match.started_at = now_ts()
            return match

    def quick_match(self, address: str) -> Match:
        """Seat the player at the first open table, or open one for them."""
        address = normalize_address(address)
        self._require_player(address)
        with self._lock:
            for match in self._matches.values():
                if (
                    match.state is MatchState.WAITING_FOR_OPPONENT
                    and match.tournament_id is None
                    and not match.has_seat(address)
                ):
                    return self.join_heads_up_match(match.id, address)
            return self.create_heads_up_match(address)

    def cancel_match(self, match_id: str, address: str) -> Match:
        address = normalize_address(address)
        with self._lock:
            match = self._get_match(match_id)
            if not match.has_seat(address):
                raise LobbyError("Only a seated player can cancel this table.")
            if match.state is MatchState.COMPLETED:
                raise LobbyError("This bout has already finished.")
            match.state = MatchState.CANCELLED
            match.ended_at = now_ts()
            return match

    # ------------------------------------------------------------------
    # Tournaments (GG Poker style eight-max sit-and-go)
    # ------------------------------------------------------------------
    def create_tournament(
        self, host: str, name: str | None = None, buy_in: Decimal | None = None
    ) -> Tournament:
        host = normalize_address(host)
        player = self._require_player(host)
        with self._lock:
            tournament = Tournament(
                id=new_id("trn", 12),
                name=(name or f"{player.username}'s 8-Max").strip()[:48],
                host=host,
                seat_limit=self.seat_limit,
                prize_pool=Decimal(buy_in or 0) * self.seat_limit,
            )
            self._tournaments[tournament.id] = tournament
            self.register_in_tournament(tournament.id, host)
            return tournament

    def register_in_tournament(self, tournament_id: str, address: str) -> Tournament:
        address = normalize_address(address)
        self._require_player(address)
        with self._lock:
            tournament = self._get_tournament(tournament_id)
            if tournament.status is not TournamentStatus.REGISTRATION:
                raise LobbyError("Registration for this tournament is closed.")
            if tournament.is_entrant(address):
                raise LobbyError("You are already registered for this tournament.")
            if tournament.seats_available <= 0:
                raise LobbyError("This tournament is full.")
            tournament.entrants.append(address)
            if len(tournament.entrants) == tournament.seat_limit:
                self._start_tournament(tournament)
            return tournament

    def unregister_from_tournament(
        self, tournament_id: str, address: str
    ) -> Tournament:
        address = normalize_address(address)
        with self._lock:
            tournament = self._get_tournament(tournament_id)
            if tournament.status is not TournamentStatus.REGISTRATION:
                raise LobbyError("The tournament has already started.")
            tournament.entrants = [
                e for e in tournament.entrants if e.lower() != address.lower()
            ]
            if not tournament.entrants:
                tournament.status = TournamentStatus.CANCELLED
                tournament.ended_at = now_ts()
            return tournament

    def _start_tournament(self, tournament: Tournament) -> None:
        seats = list(tournament.entrants)
        self._rng.shuffle(seats)
        tournament.entrants = seats
        tournament.status = TournamentStatus.IN_PROGRESS
        tournament.started_at = now_ts()
        tournament.rounds.append(self._build_round(tournament, seats, round_number=1))

    def _build_round(
        self, tournament: Tournament, seats: list[str], round_number: int
    ) -> list[str]:
        match_ids: list[str] = []
        for index in range(0, len(seats) - 1, 2):
            match = Match(
                id=new_id("tm", 11),
                player1=seats[index],
                player2=seats[index + 1],
                state=MatchState.IN_PROGRESS,
                tournament_id=tournament.id,
                round_number=round_number,
                started_at=now_ts(),
            )
            self._matches[match.id] = match
            match_ids.append(match.id)
        return match_ids

    def _advance_tournament(self, tournament: Tournament) -> None:
        """Build the next bracket round once the current round is complete."""
        if tournament.status is not TournamentStatus.IN_PROGRESS:
            return
        current_round = tournament.rounds[-1]
        matches = [self._matches[mid] for mid in current_round]
        if any(m.state is not MatchState.COMPLETED for m in matches):
            return

        winners = [m.winner for m in matches if m.winner]
        if len(winners) == 1:
            tournament.champion = winners[0]
            belt = ChampionshipBelt(tournament.id, tournament.name)
            tournament.championship_belt = belt
            champion = self.get_player(winners[0])
            if champion:
                champion.championship_belts.append(belt)
            tournament.status = TournamentStatus.COMPLETED
            tournament.ended_at = now_ts()
            return
        if len(winners) < 2 or len(winners) % 2 != 0:
            return
        tournament.rounds.append(
            self._build_round(tournament, winners, round_number=len(tournament.rounds) + 1)
        )

    # ------------------------------------------------------------------
    # Results and rewards
    # ------------------------------------------------------------------
    def report_winner(
        self,
        match_id: str,
        winner: str,
        reporter: str,
        player1_score: int = 0,
        player2_score: int = 0,
        rounds_completed: int = 0,
    ) -> tuple[Match, Reward | None]:
        """Record the result of a bout and issue the winner's ARC claim."""
        winner = normalize_address(winner)
        reporter = normalize_address(reporter)
        with self._lock:
            match = self._get_match(match_id)
            if not match.has_seat(reporter):
                raise LobbyError("Only a seated player can report this result.")
            if not match.has_seat(winner):
                raise LobbyError("The winner must be seated at this table.")
            if match.state is MatchState.COMPLETED:
                raise LobbyError("This bout has already been reported.")
            if match.state is MatchState.CANCELLED:
                raise LobbyError("This bout was cancelled.")
            if match.player2 is None:
                raise LobbyError("This bout never had an opponent.")

            match.winner = winner
            match.state = MatchState.COMPLETED
            match.player1_score = player1_score
            match.player2_score = player2_score
            match.rounds_completed = rounds_completed
            match.ended_at = now_ts()

            loser = match.opponent_of(winner)
            winner_player = self.get_player(winner)
            loser_player = self.get_player(loser) if loser else None
            if winner_player:
                winner_player.wins += 1
            if loser_player:
                loser_player.losses += 1

            if match.tournament_id:
                tournament = self._tournaments.get(match.tournament_id)
                if tournament:
                    self._advance_tournament(tournament)

            reward = self._issue_reward(match)
            return match, reward

    def _issue_reward(self, match: Match) -> Reward | None:
        """Issue the flat per-game Arcade1870 claim for a completed bout."""
        if self.reward_issuer is None or match.winner is None:
            return None
        try:
            reward = self.reward_issuer.issue_claim(match.winner, match.id)
        except RewardError:
            return None
        match.reward_amount = reward.amount
        return reward

    # ------------------------------------------------------------------
    # Lobby snapshot
    # ------------------------------------------------------------------
    def lobby(self) -> dict[str, Any]:
        with self._lock:
            matches = sorted(
                (m for m in self._matches.values() if m.tournament_id is None),
                key=lambda m: m.created_at,
                reverse=True,
            )[:LOBBY_MATCH_LIMIT]
            tournaments = sorted(
                self._tournaments.values(), key=lambda t: t.created_at, reverse=True
            )[:LOBBY_TOURNAMENT_LIMIT]
            return {
                "headsUpMatches": [self._describe_match(m) for m in matches],
                "tournaments": [self._describe_tournament(t) for t in tournaments],
                "playersOnline": len(self._players),
            }

    def _describe_match(self, match: Match) -> dict[str, Any]:
        data = match.to_dict()
        data["player1Name"] = self._name_of(match.player1)
        data["player2Name"] = self._name_of(match.player2)
        return data

    def _describe_tournament(self, tournament: Tournament) -> dict[str, Any]:
        data = tournament.to_dict()
        data["entrantNames"] = [self._name_of(e) for e in tournament.entrants]
        data["bracket"] = [
            [self._describe_match(self._matches[mid]) for mid in rnd]
            for rnd in tournament.rounds
        ]
        data["championName"] = self._name_of(tournament.champion)
        return data

    def _name_of(self, address: str | None) -> str | None:
        if not address:
            return None
        player = self.get_player(address)
        return player.username if player else display_name(address, None)

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------
    def get_match(self, match_id: str) -> Match | None:
        return self._matches.get(match_id)

    def get_tournament(self, tournament_id: str) -> Tournament | None:
        return self._tournaments.get(tournament_id)

    def _get_match(self, match_id: str) -> Match:
        match = self._matches.get(match_id)
        if match is None:
            raise LobbyError(f"Unknown table {match_id!r}.")
        return match

    def _get_tournament(self, tournament_id: str) -> Tournament:
        tournament = self._tournaments.get(tournament_id)
        if tournament is None:
            raise LobbyError(f"Unknown tournament {tournament_id!r}.")
        return tournament

    def describe_match(self, match: Match) -> dict[str, Any]:
        return self._describe_match(match)

    def describe_tournament(self, tournament: Tournament) -> dict[str, Any]:
        return self._describe_tournament(tournament)
