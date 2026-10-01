"""Terminal client - headless lobby browser and text-mode bouts.

Browse the GG Poker style lobby, open or join a heads-up table, register for an
eight-max sit-and-go, and play a practice bout without pygame::

    python -m criscyborg.client.terminal practice --difficulty Expert
    python -m criscyborg.client.terminal lobby --server http://localhost:8000
    python -m criscyborg.client.terminal sitngo --server http://localhost:8000 \\
        --private-key 0x... --name "Southpaw"
"""

from __future__ import annotations

import argparse
import random
import sys

from ..models import Difficulty
from ..game.ai import BoxerAI
from ..game.engine import Action, Boxer, BoxingMatch

PROMPT = "[j] jab  [k] hook  [l] special  [d] dodge  [w] wait  [q] quit > "
INPUT_ACTIONS = {
    "j": Action.LEFT_PUNCH,
    "k": Action.RIGHT_PUNCH,
    "l": Action.SPECIAL,
    "d": Action.DODGE,
    "w": Action.IDLE,
}


def _render(match: BoxingMatch) -> None:
    b1, b2 = match.boxer1, match.boxer2
    print(
        f"\nRound {match.current_round}/{match.total_rounds}"
        f"  |  {int(max(0.0, match.round_time_remaining))}s left"
    )
    for boxer in (b1, b2):
        bar = "#" * int(boxer.current_health / 5)
        print(
            f"  {boxer.name:<16} {bar:<20} "
            f"{boxer.current_health:5.1f} hp  {boxer.stamina:5.1f} sta  "
            f"{boxer.score:4d} pts"
        )
    for event in match.events[-2:]:
        print(f"  * {event}")


def play_practice(
    name: str, opponent: str, difficulty: Difficulty, seed: int | None = None
) -> Boxer | None:
    rng = random.Random(seed)
    match = BoxingMatch(
        boxer1=Boxer.from_difficulty(name, Difficulty.MEDIUM),
        boxer2=Boxer.from_difficulty(opponent, difficulty),
        rng=rng,
    )
    ai = BoxerAI(match.boxer2, rng)
    match.start()

    while not match.is_over:
        _render(match)
        try:
            choice = input(PROMPT).strip().lower()
        except EOFError:
            break
        if choice == "q":
            break
        action = INPUT_ACTIONS.get(choice)
        if action is None:
            continue
        if action is not Action.IDLE:
            match.apply_action(match.boxer1, action)
        ai.act(match)
        # Each exchange advances the clock by a fixed tick.
        match.tick(2.0)

    if match.winner:
        print(f"\n{match.winner.name} wins the bout!")
    return match.winner


def _client(args: argparse.Namespace):
    from .api import GameApiClient

    api = GameApiClient(args.server)
    if args.private_key:
        api.login_with_private_key(args.private_key, args.name)
    return api


def show_lobby(args: argparse.Namespace) -> int:
    api = _client(args)
    lobby = api.lobby()
    print(f"Players online: {lobby['playersOnline']}")
    print("\nHeads-up tables")
    for match in lobby["headsUpMatches"]:
        print(
            f"  {match['id']}  {match['state']:<18} "
            f"{match['player1Name']} vs {match['player2Name'] or '<open seat>'}"
        )
    print("\nEight-max sit-and-gos")
    for tournament in lobby["tournaments"]:
        print(
            f"  {tournament['id']}  {tournament['name']:<28} "
            f"{tournament['status']:<13} "
            f"{len(tournament['entrants'])}/{tournament['seatLimit']} seated"
        )
    api.close()
    return 0


def heads_up(args: argparse.Namespace) -> int:
    api = _client(args)
    table = api.join_match(args.match) if args.match else api.quick_match()
    print(f"Seated at table {table['id']} ({table['state']})")
    print(f"  {table['player1Name']} vs {table['player2Name'] or 'waiting...'}")
    api.close()
    return 0


def sit_n_go(args: argparse.Namespace) -> int:
    api = _client(args)
    if args.tournament:
        tournament = api.register_tournament(args.tournament)
    else:
        tournament = api.create_tournament(args.title, args.buy_in)
    print(f"{tournament['name']} [{tournament['id']}] - {tournament['status']}")
    print(f"  Seats: {len(tournament['entrants'])}/{tournament['seatLimit']}")
    for index, bracket_round in enumerate(tournament["bracket"], start=1):
        print(f"  Round {index}")
        for match in bracket_round:
            print(
                f"    {match['id']}  {match['player1Name']} vs {match['player2Name']}"
            )
    api.close()
    return 0


def rewards(args: argparse.Namespace) -> int:
    api = _client(args)
    config = api.reward_config()
    print(
        f"Arcade1870 vault {config['vaultAddress']} on chain {config['chainId']} "
        f"- {config['rewardAmount']} ARC per completed game"
    )
    for reward in api.my_rewards()["rewards"]:
        print(
            f"  {reward['id']}  {reward['amount']} {reward['tokenSymbol']}  "
            f"{reward['status']}  game {reward['gameId']}"
        )
    api.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cris Cyborg Boxing (terminal)")
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--private-key", help="Dev key used to sign the login challenge")
    parser.add_argument("--name", default="Challenger")
    sub = parser.add_subparsers(dest="command", required=True)

    practice = sub.add_parser("practice", help="Offline bout against the AI")
    practice.add_argument("--opponent", default="Cris Cyborg")
    practice.add_argument(
        "--difficulty",
        default=Difficulty.MEDIUM.value,
        choices=[d.value for d in Difficulty],
    )
    practice.add_argument("--seed", type=int)

    sub.add_parser("lobby", help="Show open tables and sit-and-gos")

    table = sub.add_parser("headsup", help="Open or join a one-vs-one table")
    table.add_argument("--match", help="Table id to join (omit for quick seat)")

    sitngo = sub.add_parser("sitngo", help="Create or register for an 8-max sit-and-go")
    sitngo.add_argument("--tournament", help="Tournament id to register for")
    sitngo.add_argument("--title", help="Name for a new tournament")
    sitngo.add_argument("--buy-in", help="Optional ARC buy-in per seat")

    sub.add_parser("rewards", help="Show Arcade1870 reward claims")

    args = parser.parse_args(argv)

    if args.command == "practice":
        play_practice(
            args.name, args.opponent, Difficulty(args.difficulty), args.seed
        )
        return 0
    if args.command == "lobby":
        return show_lobby(args)
    if args.command == "headsup":
        return heads_up(args)
    if args.command == "sitngo":
        return sit_n_go(args)
    if args.command == "rewards":
        return rewards(args)
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
