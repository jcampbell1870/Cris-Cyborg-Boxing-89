"""Pygame front end - the 2D boxing ring, HUD and controls.

Offline practice::

    python -m criscyborg.client.pygame_client --difficulty Hard

Online bout (after the table is seated through the lobby)::

    python -m criscyborg.client.pygame_client --server http://localhost:8000 \\
        --private-key 0x... --match hu-abc123

Controls: ``A``/``D`` move, ``J`` left jab, ``K`` right hook,
``L`` special, ``Space`` dodge, ``Esc`` quit.
"""

from __future__ import annotations

import argparse
import json
import queue
import threading
from typing import Any

from ..models import Difficulty
from ..game.ai import BoxerAI
from ..game.engine import Action, Boxer, BoxingMatch, GameState

WIDTH, HEIGHT = 960, 540
FLOOR_Y = 420
FPS = 60

RING_COLOR = (32, 28, 40)
CANVAS_COLOR = (58, 44, 62)
ROPE_COLOR = (214, 84, 96)
P1_COLOR = (86, 180, 233)
P2_COLOR = (233, 108, 86)
TEXT_COLOR = (240, 240, 245)
HEALTH_BG = (70, 70, 80)
HEALTH_FG = (120, 220, 130)
STAMINA_FG = (240, 200, 90)

KEY_ACTIONS = {
    "j": Action.LEFT_PUNCH,
    "k": Action.RIGHT_PUNCH,
    "l": Action.SPECIAL,
    "space": Action.DODGE,
}


class PygameClient:
    """Renders and drives a :class:`BoxingMatch`."""

    def __init__(
        self,
        match: BoxingMatch,
        ai: BoxerAI | None = None,
        net: "MatchChannel | None" = None,
    ) -> None:
        import pygame  # imported lazily so the package works headless

        self.pygame = pygame
        self.match = match
        self.ai = ai
        self.net = net
        self.p1_x = WIDTH * 0.32
        self.p2_x = WIDTH * 0.68
        self.ai_cooldown = 0.0

        pygame.init()
        pygame.display.set_caption("Cris Cyborg Boxing 89")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)
        self.big_font = pygame.font.SysFont("consolas", 40, bold=True)

    # ------------------------------------------------------------------
    def run(self) -> Boxer | None:
        pygame = self.pygame
        self.match.start()
        running = True
        while running:
            delta = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        self._handle_key(pygame.key.name(event.key))

            self._handle_movement(delta)
            self._pump_network()
            self._update_ai(delta)
            self.match.tick(delta)
            self._draw()

            if self.match.is_over:
                self._draw_result()
                pygame.display.flip()
                pygame.time.wait(2500)
                running = False

        pygame.quit()
        return self.match.winner

    # ------------------------------------------------------------------
    def _handle_key(self, key_name: str) -> None:
        action = KEY_ACTIONS.get(key_name)
        if action is None:
            return
        self.match.apply_action(self.match.boxer1, action)
        if self.net is not None:
            self.net.send({"type": "input", "data": {"action": action.value}})

    def _handle_movement(self, delta: float) -> None:
        pygame = self.pygame
        keys = pygame.key.get_pressed()
        speed = 180 * delta
        if keys[pygame.K_a]:
            self.p1_x = max(80, self.p1_x - speed)
        if keys[pygame.K_d]:
            self.p1_x = min(self.p2_x - 90, self.p1_x + speed)

    def _pump_network(self) -> None:
        if self.net is None:
            return
        for message in self.net.drain():
            if message.get("address", "").lower() == (self.net.address or "").lower():
                continue
            if message.get("type") != "input":
                continue
            raw_action = (message.get("data") or {}).get("action")
            try:
                action = Action(raw_action)
            except ValueError:
                continue
            self.match.apply_action(self.match.boxer2, action)

    def _update_ai(self, delta: float) -> None:
        if self.ai is None:
            return
        self.ai_cooldown -= delta
        if self.ai_cooldown <= 0:
            self.ai.act(self.match)
            # Faster boxers act more often.
            self.ai_cooldown = max(0.25, 1.2 - self.ai.boxer.speed * 0.1)

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        pygame = self.pygame
        self.screen.fill(RING_COLOR)
        pygame.draw.rect(
            self.screen, CANVAS_COLOR, pygame.Rect(60, 220, WIDTH - 120, 260)
        )
        for offset in (0, 40, 80):
            pygame.draw.line(
                self.screen,
                ROPE_COLOR,
                (60, 220 + offset),
                (WIDTH - 60, 220 + offset),
                3,
            )

        self._draw_boxer(self.match.boxer1, self.p1_x, P1_COLOR)
        self._draw_boxer(self.match.boxer2, self.p2_x, P2_COLOR)
        self._draw_hud()
        pygame.display.flip()

    def _draw_boxer(self, boxer: Boxer, x: float, color: tuple[int, int, int]) -> None:
        pygame = self.pygame
        height = 60 if boxer.is_knocked_down else 130
        body = pygame.Rect(int(x) - 25, FLOOR_Y - height, 50, height)
        pygame.draw.rect(self.screen, color, body, border_radius=10)
        head_y = FLOOR_Y - height - 18
        pygame.draw.circle(self.screen, color, (int(x), head_y), 18)
        if boxer.is_dodging:
            pygame.draw.circle(self.screen, TEXT_COLOR, (int(x), head_y), 24, 2)

    def _draw_hud(self) -> None:
        self._draw_bars(self.match.boxer1, 40, align_left=True)
        self._draw_bars(self.match.boxer2, WIDTH - 40 - 340, align_left=False)

        timer = self.big_font.render(
            f"{int(max(0.0, self.match.round_time_remaining)):03d}", True, TEXT_COLOR
        )
        self.screen.blit(timer, timer.get_rect(center=(WIDTH // 2, 48)))
        round_label = self.font.render(
            f"Round {self.match.current_round}/{self.match.total_rounds}",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(round_label, round_label.get_rect(center=(WIDTH // 2, 88)))

        for index, event in enumerate(self.match.events[-3:]):
            line = self.font.render(event, True, TEXT_COLOR)
            self.screen.blit(line, (WIDTH // 2 - line.get_width() // 2, 110 + index * 22))

    def _draw_bars(self, boxer: Boxer, x: int, align_left: bool) -> None:
        pygame = self.pygame
        width = 340
        health_ratio = max(0.0, boxer.current_health / boxer.max_health)
        stamina_ratio = max(0.0, boxer.stamina / 100.0)

        pygame.draw.rect(self.screen, HEALTH_BG, pygame.Rect(x, 30, width, 22))
        pygame.draw.rect(
            self.screen, HEALTH_FG, pygame.Rect(x, 30, int(width * health_ratio), 22)
        )
        pygame.draw.rect(self.screen, HEALTH_BG, pygame.Rect(x, 56, width, 10))
        pygame.draw.rect(
            self.screen, STAMINA_FG, pygame.Rect(x, 56, int(width * stamina_ratio), 10)
        )

        label = self.font.render(
            f"{boxer.name}  {boxer.score} pts  [{boxer.rounds_won}]", True, TEXT_COLOR
        )
        rect = label.get_rect()
        rect.topleft = (x, 72) if align_left else (x + width - rect.width, 72)
        self.screen.blit(label, rect)

    def _draw_result(self) -> None:
        winner = self.match.winner.name if self.match.winner else "Draw"
        text = self.big_font.render(f"{winner} wins!", True, TEXT_COLOR)
        self.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))


class MatchChannel:
    """Background WebSocket relay for an online bout."""

    def __init__(self, url: str, address: str | None = None) -> None:
        self.url = url
        self.address = address
        self._inbox: queue.Queue[dict[str, Any]] = queue.Queue()
        self._outbox: queue.Queue[dict[str, Any]] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def send(self, message: dict[str, Any]) -> None:
        self._outbox.put(message)

    def drain(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        while True:
            try:
                messages.append(self._inbox.get_nowait())
            except queue.Empty:
                return messages

    def _run(self) -> None:
        import asyncio

        import websockets

        async def pump() -> None:
            async with websockets.connect(self.url) as socket:

                async def reader() -> None:
                    async for raw in socket:
                        try:
                            self._inbox.put(json.loads(raw))
                        except json.JSONDecodeError:
                            continue

                async def writer() -> None:
                    while not self._stop.is_set():
                        try:
                            message = self._outbox.get_nowait()
                        except queue.Empty:
                            await asyncio.sleep(0.01)
                            continue
                        await socket.send(json.dumps(message))

                await asyncio.gather(reader(), writer())

        try:
            asyncio.run(pump())
        except Exception:  # pragma: no cover - network teardown
            pass


def build_match(
    player_name: str, opponent_name: str, difficulty: Difficulty
) -> BoxingMatch:
    return BoxingMatch(
        boxer1=Boxer.from_difficulty(player_name, Difficulty.MEDIUM),
        boxer2=Boxer.from_difficulty(opponent_name, difficulty),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cris Cyborg Boxing 89 (pygame)")
    parser.add_argument("--name", default="Challenger")
    parser.add_argument("--opponent", default="Cris Cyborg")
    parser.add_argument(
        "--difficulty",
        default=Difficulty.MEDIUM.value,
        choices=[d.value for d in Difficulty],
    )
    parser.add_argument("--server", help="Base URL of the online server")
    parser.add_argument("--private-key", help="Dev key used to sign the login challenge")
    parser.add_argument("--match", help="Match id to play online")
    args = parser.parse_args(argv)

    difficulty = Difficulty(args.difficulty)
    match = build_match(args.name, args.opponent, difficulty)

    net: MatchChannel | None = None
    ai: BoxerAI | None = BoxerAI(match.boxer2)
    api = None

    if args.server and args.match and args.private_key:
        from .api import GameApiClient

        api = GameApiClient(args.server)
        api.login_with_private_key(args.private_key, args.name)
        table = api.get_match(args.match)
        opponent = (
            table["player2Name"]
            if (table["player1"] or "").lower() == (api.address or "").lower()
            else table["player1Name"]
        )
        match.boxer2.name = opponent or args.opponent
        net = MatchChannel(api.match_socket_url(args.match), api.address)
        net.start()
        ai = None

    client = PygameClient(match, ai=ai, net=net)
    winner = client.run()

    if net is not None:
        net.stop()
    if api is not None and winner is not None and args.match:
        won = winner is match.boxer1
        if won:
            result = api.report_result(
                args.match,
                winner=api.address or "",
                player1_score=match.boxer1.score,
                player2_score=match.boxer2.score,
                rounds_completed=match.current_round,
            )
            reward = result.get("reward")
            if reward:
                print(
                    f"Reward claim issued: {reward['amount']} "
                    f"{reward['tokenSymbol']} - submit claim(amount, nonce, "
                    f"deadline, signature) to vault {reward['vaultAddress']}"
                )
        api.close()

    print(f"Winner: {winner.name if winner else 'nobody'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
