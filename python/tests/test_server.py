"""End-to-end API tests: wallet login, tables, sit-and-gos and reward claims."""

from __future__ import annotations

import importlib

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

SIGNER_KEY = "0x" + "bb" * 32


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("REWARD_SIGNER_PRIVATE_KEY", SIGNER_KEY)
    monkeypatch.setenv("JWT_SECRET", "test-secret-value-at-least-32-bytes-long")
    module = importlib.import_module("criscyborg.server.app")
    module = importlib.reload(module)
    return TestClient(module.app)


def login(client: TestClient, key_byte: int, username: str) -> tuple[str, str]:
    account = Account.from_key(bytes([key_byte]) * 32)
    challenge = client.post(
        "/api/auth/challenge", json={"address": account.address}
    ).json()
    signature = Account.sign_message(
        encode_defunct(text=challenge["message"]), account.key
    ).signature.to_0x_hex()
    response = client.post(
        "/api/auth/login",
        json={
            "address": account.address,
            "signature": signature,
            "username": username,
        },
    )
    assert response.status_code == 200, response.text
    return account.address, response.json()["token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + token}


def test_login_requires_a_valid_signature(client: TestClient) -> None:
    account = Account.from_key(bytes([9]) * 32)
    client.post("/api/auth/challenge", json={"address": account.address})
    bad = Account.sign_message(
        encode_defunct(text="not the challenge"), account.key
    ).signature.to_0x_hex()
    response = client.post(
        "/api/auth/login", json={"address": account.address, "signature": bad}
    )
    assert response.status_code == 401


def test_protected_routes_reject_missing_tokens(client: TestClient) -> None:
    assert client.post("/api/matches").status_code == 401
    assert client.get("/api/players/me/rewards").status_code == 401


def test_heads_up_flow_pays_an_arcade1870_claim(client: TestClient) -> None:
    host_address, host_token = login(client, 1, "Host")
    guest_address, guest_token = login(client, 2, "Guest")

    table = client.post("/api/matches", headers=auth(host_token)).json()
    joined = client.post(
        f"/api/matches/{table['id']}/join", headers=auth(guest_token)
    ).json()
    assert joined["state"] == "InProgress"

    result = client.post(
        f"/api/matches/{table['id']}/result",
        json={
            "winner": host_address,
            "player1Score": 90,
            "player2Score": 40,
            "roundsCompleted": 3,
        },
        headers=auth(host_token),
    )
    assert result.status_code == 200, result.text
    reward = result.json()["reward"]
    assert reward["amount"] == "10"
    assert reward["tokenSymbol"] == "A1870"
    assert reward["status"] == "Issued"
    assert reward["vaultAddress"].lower() == (
        "0x1e4f6e4a382adbdb662733a19ae773d3ab8f497d"
    )

    completed = client.post(
        f"/api/rewards/{reward['id']}/complete",
        json={"transactionHash": "0x" + "cd" * 32},
        headers=auth(host_token),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "Completed"

    # The losing player must not be able to read or complete someone
    # else's claim.
    assert (
        client.get(f"/api/rewards/{reward['id']}", headers=auth(guest_token)).status_code
        == 404
    )
    assert guest_address != host_address


def test_eight_max_sit_and_go_fills_and_starts(client: TestClient) -> None:
    host_address, host_token = login(client, 3, "Host")
    tournament = client.post(
        "/api/tournaments", json={"name": "Nightly 8-Max"}, headers=auth(host_token)
    ).json()
    assert tournament["seatLimit"] == 8
    assert tournament["status"] == "Registration"

    tokens = {host_address: host_token}
    for key_byte in range(4, 11):
        address, token = login(client, key_byte, f"Boxer{key_byte}")
        tokens[address] = token
        tournament = client.post(
            f"/api/tournaments/{tournament['id']}/register", headers=auth(token)
        ).json()

    assert tournament["status"] == "InProgress"
    assert len(tournament["bracket"]) == 1
    assert len(tournament["bracket"][0]) == 4

    lobby = client.get("/api/lobby").json()
    assert lobby["tournaments"][0]["id"] == tournament["id"]
    assert tournament["championshipBelt"] is None

    for round_index in range(3):
        tournament = client.get(f"/api/tournaments/{tournament['id']}").json()
        for match in tournament["bracket"][round_index]:
            result = client.post(
                f"/api/matches/{match['id']}/result",
                json={"winner": match["player1"]},
                headers=auth(tokens[match["player1"]]),
            )
            assert result.status_code == 200, result.text

    tournament = client.get(f"/api/tournaments/{tournament['id']}").json()
    assert tournament["status"] == "Completed"
    belt = tournament["championshipBelt"]
    assert belt["tournamentId"] == tournament["id"]
    assert belt["tournamentName"] == "Nightly 8-Max"
    assert client.get("/api/lobby").json()["tournaments"][0]["championshipBelt"] == belt
    for address, token in tokens.items():
        player = client.get("/api/players/me", headers=auth(token)).json()
        assert player["championshipBelts"] == ([belt] if address == tournament["champion"] else [])


def test_reward_config_exposes_shared_vault(client: TestClient) -> None:
    config = client.get("/api/rewards/config").json()
    assert config["tokenAddress"].lower() == (
        "0x8eddd4edea39c5b5f77662453600f53a202ee47c"
    )
    assert config["vaultAddress"].lower() == (
        "0x1e4f6e4a382adbdb662733a19ae773d3ab8f497d"
    )
    assert config["rewardAmount"] == "10"
    assert config["chainId"] == 1
    assert config["configured"] is True
    assert client.get("/health/reward-issuer").json()["status"] == "ok"
