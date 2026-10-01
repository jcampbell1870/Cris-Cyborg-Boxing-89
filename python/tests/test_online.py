"""Tests for the GG Poker style lobby: heads-up tables and 8-max sit-and-gos."""

from __future__ import annotations

import random

import pytest
from eth_account import Account

from criscyborg.config import BlockchainConfig
from criscyborg.models import MatchState, TournamentStatus
from criscyborg.online import LobbyError, OnlineCompetitionService
from criscyborg.rewards import RewardIssuer

SIGNER_KEY = "0x" + "aa" * 32


def make_service() -> OnlineCompetitionService:
    issuer = RewardIssuer(BlockchainConfig(reward_signer_private_key=SIGNER_KEY))
    return OnlineCompetitionService(reward_issuer=issuer, rng=random.Random(7))


def wallets(count: int) -> list[str]:
    return [Account.from_key(bytes([i + 1]) * 32).address for i in range(count)]


def seat_players(service: OnlineCompetitionService, count: int) -> list[str]:
    addresses = wallets(count)
    for index, address in enumerate(addresses):
        service.upsert_player(address, f"Boxer{index}")
    return addresses


# ----------------------------------------------------------------------
# Heads-up
# ----------------------------------------------------------------------
def test_heads_up_table_seats_two_players() -> None:
    service = make_service()
    host, guest = seat_players(service, 2)

    match = service.create_heads_up_match(host)
    assert match.state is MatchState.WAITING_FOR_OPPONENT

    joined = service.join_heads_up_match(match.id, guest)
    assert joined.state is MatchState.IN_PROGRESS
    assert joined.player2 == guest


def test_host_cannot_join_own_table() -> None:
    service = make_service()
    (host,) = seat_players(service, 1)
    match = service.create_heads_up_match(host)
    with pytest.raises(LobbyError):
        service.join_heads_up_match(match.id, host)


def test_quick_match_seats_at_an_open_table() -> None:
    service = make_service()
    host, guest = seat_players(service, 2)
    opened = service.quick_match(host)
    seated = service.quick_match(guest)
    assert seated.id == opened.id
    assert seated.state is MatchState.IN_PROGRESS


def test_only_a_seated_player_can_report_a_result() -> None:
    service = make_service()
    host, guest, stranger = seat_players(service, 3)
    match = service.create_heads_up_match(host)
    service.join_heads_up_match(match.id, guest)
    with pytest.raises(LobbyError):
        service.report_winner(match.id, host, stranger)


def test_winner_must_be_seated() -> None:
    service = make_service()
    host, guest, stranger = seat_players(service, 3)
    match = service.create_heads_up_match(host)
    service.join_heads_up_match(match.id, guest)
    with pytest.raises(LobbyError):
        service.report_winner(match.id, stranger, host)


def test_result_issues_a_reward_and_updates_records() -> None:
    service = make_service()
    host, guest = seat_players(service, 2)
    match = service.create_heads_up_match(host)
    service.join_heads_up_match(match.id, guest)

    completed, reward = service.report_winner(match.id, host, host, 120, 80, 3)
    assert completed.state is MatchState.COMPLETED
    assert reward is not None
    assert reward.recipient == host
    assert str(reward.amount) == "10"
    assert reward.game_id == match.id.lower()
    assert service.get_player(host).wins == 1
    assert service.get_player(guest).losses == 1

    with pytest.raises(LobbyError):
        service.report_winner(match.id, host, host)


# ----------------------------------------------------------------------
# Eight-max sit-and-go
# ----------------------------------------------------------------------
def test_tournament_auto_starts_when_eight_seats_fill() -> None:
    service = make_service()
    addresses = seat_players(service, 8)
    tournament = service.create_tournament(addresses[0], "Friday 8-Max")
    assert tournament.status is TournamentStatus.REGISTRATION

    for address in addresses[1:]:
        tournament = service.register_in_tournament(tournament.id, address)

    assert tournament.status is TournamentStatus.IN_PROGRESS
    assert tournament.seats_available == 0
    assert len(tournament.rounds) == 1
    assert len(tournament.rounds[0]) == 4


def test_tournament_rejects_duplicate_and_overfull_registration() -> None:
    service = make_service()
    addresses = seat_players(service, 9)
    tournament = service.create_tournament(addresses[0])
    with pytest.raises(LobbyError):
        service.register_in_tournament(tournament.id, addresses[0])
    for address in addresses[1:8]:
        service.register_in_tournament(tournament.id, address)
    with pytest.raises(LobbyError):
        service.register_in_tournament(tournament.id, addresses[8])


def test_full_bracket_plays_down_to_a_champion() -> None:
    service = make_service()
    addresses = seat_players(service, 8)
    tournament = service.create_tournament(addresses[0])
    for address in addresses[1:]:
        service.register_in_tournament(tournament.id, address)

    expected_rounds = [4, 2, 1]
    for round_index, expected in enumerate(expected_rounds):
        current = tournament.rounds[round_index]
        assert len(current) == expected
        for match_id in current:
            match = service.get_match(match_id)
            service.report_winner(match_id, match.player1, match.player1)

    assert tournament.status is TournamentStatus.COMPLETED
    assert tournament.champion is not None
    assert len(tournament.rounds) == 3
    belt = tournament.to_dict()["championshipBelt"]
    assert belt["tournamentId"] == tournament.id
    assert belt["tournamentName"] == tournament.name
    assert service.get_player(tournament.champion).to_dict()["championshipBelts"] == [belt]
    assert service.describe_tournament(tournament)["championshipBelt"] == belt
    assert service.lobby()["tournaments"][0]["championshipBelt"] == belt
    for address in addresses:
        if address != tournament.champion:
            assert service.get_player(address).championship_belts == []
    # Every completed bout, including the final, pays its flat ARC claim.
    assert len(service.reward_issuer.for_recipient(tournament.champion)) == 3
    with pytest.raises(LobbyError):
        final = tournament.rounds[-1][0]
        service.report_winner(final, tournament.champion, tournament.champion)
    service._advance_tournament(tournament)
    assert len(service.get_player(tournament.champion).championship_belts) == 1


def test_no_belt_for_incomplete_tournament_or_heads_up_win() -> None:
    service = make_service()
    addresses = seat_players(service, 8)
    tournament = service.create_tournament(addresses[0])
    for address in addresses[1:]:
        service.register_in_tournament(tournament.id, address)
    first = service.get_match(tournament.rounds[0][0])
    service.report_winner(first.id, first.player1, first.player1)
    assert tournament.championship_belt is None
    assert all(not service.get_player(address).championship_belts for address in addresses)

    match = service.create_heads_up_match(addresses[0])
    service.join_heads_up_match(match.id, addresses[1])
    service.report_winner(match.id, addresses[0], addresses[0])
    assert service.get_player(addresses[0]).championship_belts == []


def test_unregister_before_start_frees_the_seat() -> None:
    service = make_service()
    addresses = seat_players(service, 3)
    tournament = service.create_tournament(addresses[0])
    service.register_in_tournament(tournament.id, addresses[1])
    service.unregister_from_tournament(tournament.id, addresses[1])
    assert tournament.seats_available == 7
    service.register_in_tournament(tournament.id, addresses[2])
    assert tournament.is_entrant(addresses[2])


def test_tournament_matches_cannot_be_joined_from_the_lobby() -> None:
    service = make_service()
    addresses = seat_players(service, 9)
    tournament = service.create_tournament(addresses[0])
    for address in addresses[1:8]:
        service.register_in_tournament(tournament.id, address)
    bracket_match_id = tournament.rounds[0][0]
    with pytest.raises(LobbyError):
        service.join_heads_up_match(bracket_match_id, addresses[8])


def test_lobby_snapshot_lists_tables_and_tournaments() -> None:
    service = make_service()
    addresses = seat_players(service, 2)
    service.create_heads_up_match(addresses[0])
    service.create_tournament(addresses[1], "Late Night 8-Max")

    lobby = service.lobby()
    assert lobby["playersOnline"] == 2
    assert len(lobby["headsUpMatches"]) == 1
    assert lobby["tournaments"][0]["name"] == "Late Night 8-Max"
    assert lobby["tournaments"][0]["seatLimit"] == 8
