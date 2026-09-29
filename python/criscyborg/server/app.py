"""FastAPI server: wallet auth, GG Poker style lobby, and ARC reward claims.

Run it with::

    uvicorn criscyborg.server.app:app --reload
"""

from __future__ import annotations

import asyncio
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from ..auth import AuthError, AuthService
from ..config import BlockchainConfig, ServerConfig
from ..models import RewardStatus
from ..online import LobbyError, OnlineCompetitionService
from ..rewards import RewardError, RewardIssuer

server_config = ServerConfig.from_env()
blockchain_config = BlockchainConfig.from_env()
auth_service = AuthService(server_config)
reward_issuer = RewardIssuer(blockchain_config)
lobby_service = OnlineCompetitionService(
    reward_issuer=reward_issuer, seat_limit=server_config.tournament_seat_limit
)

app = FastAPI(title="Cris Cyborg Boxing 89", version="1.0.0")
bearer_scheme = HTTPBearer(auto_error=False)


# ----------------------------------------------------------------------
# Request models
# ----------------------------------------------------------------------
class ChallengeRequest(BaseModel):
    address: str


class LoginRequest(BaseModel):
    address: str
    signature: str
    username: str | None = None


class CreateMatchRequest(BaseModel):
    pass


class CreateTournamentRequest(BaseModel):
    name: str | None = None
    buyIn: str | None = None


class ResultRequest(BaseModel):
    winner: str
    player1Score: int = Field(default=0, ge=0)
    player2Score: int = Field(default=0, ge=0)
    roundsCompleted: int = Field(default=0, ge=0)


class CompleteRewardRequest(BaseModel):
    transactionHash: str


# ----------------------------------------------------------------------
# Dependencies
# ----------------------------------------------------------------------
def current_address(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing session token.")
    try:
        return auth_service.address_from_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


CurrentAddress = Annotated[str, Depends(current_address)]


def _lobby_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LobbyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ----------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------
@app.post("/api/auth/challenge")
def create_challenge(request: ChallengeRequest) -> dict[str, Any]:
    try:
        challenge = auth_service.create_challenge(request.address)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"address": challenge.address, "message": challenge.message}


@app.post("/api/auth/login")
def login(request: LoginRequest) -> dict[str, Any]:
    try:
        token = auth_service.login(request.address, request.signature)
    except (AuthError, ValueError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    player = lobby_service.upsert_player(request.address, request.username)
    return {"token": token, "player": player.to_dict()}


@app.get("/api/players/me")
def me(address: CurrentAddress) -> dict[str, Any]:
    player = lobby_service.get_player(address)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found.")
    return player.to_dict()


@app.get("/api/players/leaderboard")
def leaderboard() -> dict[str, Any]:
    return {"players": [p.to_dict() for p in lobby_service.leaderboard()]}


# ----------------------------------------------------------------------
# Lobby / heads-up tables
# ----------------------------------------------------------------------
@app.get("/api/lobby")
def lobby() -> dict[str, Any]:
    return lobby_service.lobby()


@app.post("/api/matches")
def create_match(address: CurrentAddress) -> dict[str, Any]:
    match = _lobby_call(lobby_service.create_heads_up_match, address)
    return lobby_service.describe_match(match)


@app.post("/api/matches/quick")
def quick_match(address: CurrentAddress) -> dict[str, Any]:
    match = _lobby_call(lobby_service.quick_match, address)
    return lobby_service.describe_match(match)


@app.post("/api/matches/{match_id}/join")
def join_match(match_id: str, address: CurrentAddress) -> dict[str, Any]:
    match = _lobby_call(lobby_service.join_heads_up_match, match_id, address)
    return lobby_service.describe_match(match)


@app.post("/api/matches/{match_id}/cancel")
def cancel_match(match_id: str, address: CurrentAddress) -> dict[str, Any]:
    match = _lobby_call(lobby_service.cancel_match, match_id, address)
    return lobby_service.describe_match(match)


@app.get("/api/matches/{match_id}")
def get_match(match_id: str) -> dict[str, Any]:
    match = lobby_service.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Unknown table.")
    return lobby_service.describe_match(match)


@app.post("/api/matches/{match_id}/result")
async def report_result(
    match_id: str, request: ResultRequest, address: CurrentAddress
) -> dict[str, Any]:
    match, reward = _lobby_call(
        lobby_service.report_winner,
        match_id,
        request.winner,
        address,
        request.player1Score,
        request.player2Score,
        request.roundsCompleted,
    )
    payload = {
        "match": lobby_service.describe_match(match),
        "reward": reward.to_dict() if reward else None,
    }
    await manager.broadcast(match_id, {"type": "matchEnded", **payload})
    return payload


# ----------------------------------------------------------------------
# Tournaments (eight-max sit-and-go)
# ----------------------------------------------------------------------
@app.post("/api/tournaments")
def create_tournament(
    request: CreateTournamentRequest, address: CurrentAddress
) -> dict[str, Any]:
    buy_in = None
    if request.buyIn:
        try:
            buy_in = Decimal(request.buyIn)
        except InvalidOperation as exc:
            raise HTTPException(status_code=400, detail="Invalid buy-in.") from exc
        if buy_in < 0:
            raise HTTPException(status_code=400, detail="Buy-in cannot be negative.")
    tournament = _lobby_call(
        lobby_service.create_tournament, address, request.name, buy_in
    )
    return lobby_service.describe_tournament(tournament)


@app.post("/api/tournaments/{tournament_id}/register")
def register_tournament(tournament_id: str, address: CurrentAddress) -> dict[str, Any]:
    tournament = _lobby_call(
        lobby_service.register_in_tournament, tournament_id, address
    )
    return lobby_service.describe_tournament(tournament)


@app.post("/api/tournaments/{tournament_id}/unregister")
def unregister_tournament(
    tournament_id: str, address: CurrentAddress
) -> dict[str, Any]:
    tournament = _lobby_call(
        lobby_service.unregister_from_tournament, tournament_id, address
    )
    return lobby_service.describe_tournament(tournament)


@app.get("/api/tournaments/{tournament_id}")
def get_tournament(tournament_id: str) -> dict[str, Any]:
    tournament = lobby_service.get_tournament(tournament_id)
    if tournament is None:
        raise HTTPException(status_code=404, detail="Unknown tournament.")
    return lobby_service.describe_tournament(tournament)


# ----------------------------------------------------------------------
# Arcade1870 rewards
# ----------------------------------------------------------------------
@app.get("/api/rewards/config")
def reward_config() -> dict[str, Any]:
    cfg = blockchain_config
    return {
        "tokenAddress": cfg.token_address,
        "vaultAddress": cfg.reward_vault_address,
        "chainId": cfg.chain_id,
        "rewardAmount": str(cfg.reward_amount),
        "tokenDecimals": cfg.token_decimals,
        "claimTtlSeconds": cfg.effective_claim_ttl_seconds,
        "configured": cfg.is_configured,
    }


@app.get("/api/rewards/{reward_id}")
def get_reward(reward_id: str, address: CurrentAddress) -> dict[str, Any]:
    reward = reward_issuer.get(reward_id)
    if reward is None or reward.recipient.lower() != address.lower():
        raise HTTPException(status_code=404, detail="Unknown reward.")
    return reward.to_dict()


@app.get("/api/players/me/rewards")
def my_rewards(address: CurrentAddress) -> dict[str, Any]:
    return {"rewards": [r.to_dict() for r in reward_issuer.for_recipient(address)]}


@app.post("/api/rewards/{reward_id}/complete")
def complete_reward(
    reward_id: str, request: CompleteRewardRequest, address: CurrentAddress
) -> dict[str, Any]:
    reward = reward_issuer.get(reward_id)
    if reward is None or reward.recipient.lower() != address.lower():
        raise HTTPException(status_code=404, detail="Unknown reward.")
    if reward.status is RewardStatus.COMPLETED:
        return reward.to_dict()
    try:
        return reward_issuer.complete(reward_id, request.transactionHash).to_dict()
    except RewardError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/health/reward-issuer")
def reward_issuer_health() -> dict[str, Any]:
    healthy = blockchain_config.is_configured
    return {
        "status": "ok" if healthy else "unconfigured",
        "vaultAddress": blockchain_config.reward_vault_address,
        "chainId": blockchain_config.chain_id,
    }


# ----------------------------------------------------------------------
# Realtime match channel
# ----------------------------------------------------------------------
class ConnectionManager:
    """Relays realtime bout traffic to everyone seated at (or watching) a table."""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, match_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms.setdefault(match_id, set()).add(websocket)

    async def disconnect(self, match_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(match_id)
            if room:
                room.discard(websocket)
                if not room:
                    self._rooms.pop(match_id, None)

    async def broadcast(self, match_id: str, message: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._rooms.get(match_id, ()))
        for websocket in targets:
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(match_id, websocket)


manager = ConnectionManager()


@app.websocket("/ws/match/{match_id}")
async def match_socket(websocket: WebSocket, match_id: str, token: str = "") -> None:
    try:
        address = auth_service.address_from_token(token)
    except AuthError:
        await websocket.close(code=4401)
        return

    match = lobby_service.get_match(match_id)
    if match is None:
        await websocket.close(code=4404)
        return
    if not match.has_seat(address):
        await websocket.close(code=4403)
        return

    await manager.connect(match_id, websocket)
    await manager.broadcast(match_id, {"type": "playerJoined", "address": address})
    try:
        while True:
            payload = await websocket.receive_json()
            payload_type = str(payload.get("type", "input"))
            if payload_type not in {"input", "state", "chat"}:
                continue
            await manager.broadcast(
                match_id,
                {"type": payload_type, "address": address, "data": payload.get("data")},
            )
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(match_id, websocket)
        await manager.broadcast(match_id, {"type": "playerLeft", "address": address})
