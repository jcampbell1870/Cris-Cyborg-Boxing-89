"""HTTP/WebSocket client for the Cris Cyborg Boxing online services."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct


class ApiError(Exception):
    """Raised when the server rejects a request."""


class GameApiClient:
    """Thin wrapper around the REST API, mirroring the C# ``GameAPIClient``."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self.token: str | None = None
        self.address: str | None = None

    # ------------------------------------------------------------------
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GameApiClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self.token} if self.token else {}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(
            method, path, headers=self._headers(), **kwargs
        )
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except json.JSONDecodeError:
                detail = response.text
            raise ApiError(f"{response.status_code}: {detail}")
        return response.json()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    def login_with_private_key(self, private_key: str, username: str | None = None):
        """Sign the server challenge locally (development / bot accounts).

        Production players sign the same challenge in MetaMask instead - the
        server only ever sees the resulting signature.
        """
        account = Account.from_key(private_key)
        challenge = self._request(
            "POST", "/api/auth/challenge", json={"address": account.address}
        )
        signature = Account.sign_message(
            encode_defunct(text=challenge["message"]), private_key
        ).signature.to_0x_hex()
        result = self.login_with_signature(account.address, signature, username)
        return result

    def login_with_signature(
        self, address: str, signature: str, username: str | None = None
    ) -> dict[str, Any]:
        result = self._request(
            "POST",
            "/api/auth/login",
            json={"address": address, "signature": signature, "username": username},
        )
        self.token = result["token"]
        self.address = result["player"]["address"]
        return result

    def request_challenge(self, address: str) -> dict[str, Any]:
        return self._request("POST", "/api/auth/challenge", json={"address": address})

    # ------------------------------------------------------------------
    # Lobby
    # ------------------------------------------------------------------
    def lobby(self) -> dict[str, Any]:
        return self._request("GET", "/api/lobby")

    def leaderboard(self) -> dict[str, Any]:
        return self._request("GET", "/api/players/leaderboard")

    def create_match(self) -> dict[str, Any]:
        return self._request("POST", "/api/matches")

    def quick_match(self) -> dict[str, Any]:
        return self._request("POST", "/api/matches/quick")

    def join_match(self, match_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/matches/{match_id}/join")

    def cancel_match(self, match_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/matches/{match_id}/cancel")

    def get_match(self, match_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/matches/{match_id}")

    def report_result(
        self,
        match_id: str,
        winner: str,
        player1_score: int = 0,
        player2_score: int = 0,
        rounds_completed: int = 0,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/matches/{match_id}/result",
            json={
                "winner": winner,
                "player1Score": player1_score,
                "player2Score": player2_score,
                "roundsCompleted": rounds_completed,
            },
        )

    # ------------------------------------------------------------------
    # Tournaments
    # ------------------------------------------------------------------
    def create_tournament(
        self, name: str | None = None, buy_in: str | None = None
    ) -> dict[str, Any]:
        return self._request(
            "POST", "/api/tournaments", json={"name": name, "buyIn": buy_in}
        )

    def register_tournament(self, tournament_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/tournaments/{tournament_id}/register")

    def unregister_tournament(self, tournament_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/tournaments/{tournament_id}/unregister")

    def get_tournament(self, tournament_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/tournaments/{tournament_id}")

    # ------------------------------------------------------------------
    # Rewards
    # ------------------------------------------------------------------
    def reward_config(self) -> dict[str, Any]:
        return self._request("GET", "/api/rewards/config")

    def my_rewards(self) -> dict[str, Any]:
        return self._request("GET", "/api/players/me/rewards")

    def complete_reward(self, reward_id: str, transaction_hash: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/rewards/{reward_id}/complete",
            json={"transactionHash": transaction_hash},
        )

    # ------------------------------------------------------------------
    def match_socket_url(self, match_id: str) -> str:
        scheme = "wss" if self.base_url.startswith("https") else "ws"
        host = self.base_url.split("://", 1)[-1]
        query = urlencode({"token": self.token or ""})
        return f"{scheme}://{host}/ws/match/{match_id}?{query}"
