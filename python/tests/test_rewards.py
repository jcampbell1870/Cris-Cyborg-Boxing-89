"""Tests for the Arcade1870 reward payout system."""

from __future__ import annotations

import time
from decimal import Decimal

import pytest
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak, to_checksum_address

from criscyborg.config import (
    DEFAULT_REWARD_VAULT_ADDRESS,
    DEFAULT_TOKEN_ADDRESS,
    BlockchainConfig,
)
from criscyborg.rewards import RewardError, RewardIssuer

SIGNER_KEY = "0x" + "11" * 32


@pytest.fixture
def issuer() -> RewardIssuer:
    return RewardIssuer(BlockchainConfig(reward_signer_private_key=SIGNER_KEY))


def test_defaults_match_crypto_hockey() -> None:
    config = BlockchainConfig()
    assert config.token_address == DEFAULT_TOKEN_ADDRESS
    assert config.reward_vault_address == DEFAULT_REWARD_VAULT_ADDRESS
    assert config.reward_amount == Decimal("10")
    assert config.token_decimals == 18
    assert config.claim_ttl_seconds == 600
    assert config.chain_id == 1
    assert config.reward_amount_wei == 10 * 10**18


def test_issue_claim_signs_a_verifiable_vault_claim(issuer: RewardIssuer) -> None:
    recipient = Account.from_key("0x" + "22" * 32).address
    reward = issuer.issue_claim(recipient, "hu-abc123")

    assert reward.amount == Decimal("10")
    assert reward.amount_wei == 10 * 10**18
    assert reward.vault_address == to_checksum_address(DEFAULT_REWARD_VAULT_ADDRESS)
    assert reward.token_address == to_checksum_address(DEFAULT_TOKEN_ADDRESS)
    assert reward.token_symbol == "A1870"
    assert reward.deadline > int(time.time())
    assert reward.deadline <= int(time.time()) + 600
    assert issuer.recover_signer(reward) == issuer.signer_address


def test_digest_matches_the_solidity_vault(issuer: RewardIssuer) -> None:
    """Recompute the digest exactly as Arcade1870RewardVault.claim() does."""
    recipient = Account.from_key("0x" + "33" * 32).address
    amount, nonce, deadline = 10**18, 1, 2
    payload = issuer.typed_data(recipient, amount, nonce, deadline)

    assert payload["domain"]["name"] == "Arcade1870RewardVault"
    assert payload["domain"]["version"] == "1"
    assert payload["domain"]["chainId"] == 1
    assert [field["name"] for field in payload["types"]["Claim"]] == [
        "recipient",
        "amount",
        "nonce",
        "deadline",
    ]

    domain_separator = keccak(
        encode(
            ["bytes32", "bytes32", "bytes32", "uint256", "address"],
            [
                keccak(
                    text="EIP712Domain(string name,string version,"
                    "uint256 chainId,address verifyingContract)"
                ),
                keccak(text="Arcade1870RewardVault"),
                keccak(text="1"),
                1,
                to_checksum_address(DEFAULT_REWARD_VAULT_ADDRESS),
            ],
        )
    )
    struct_hash = keccak(
        encode(
            ["bytes32", "address", "uint256", "uint256", "uint256"],
            [
                keccak(
                    text="Claim(address recipient,uint256 amount,"
                    "uint256 nonce,uint256 deadline)"
                ),
                recipient,
                amount,
                nonce,
                deadline,
            ],
        )
    )
    expected_digest = keccak(b"\x19\x01" + domain_separator + struct_hash)

    signable = encode_typed_data(full_message=payload)
    assert _hash_eip712_message(signable) == expected_digest

    signature = issuer.sign_claim(recipient, amount, nonce, deadline)
    assert Account.recover_message(signable, signature=signature) == (
        issuer.signer_address
    )


def _hash_eip712_message(signable) -> bytes:
    return keccak(b"\x19" + signable.version + signable.header + signable.body)


def test_same_game_is_only_rewarded_once(issuer: RewardIssuer) -> None:
    recipient = Account.from_key("0x" + "44" * 32).address
    first = issuer.issue_claim(recipient, "hu-dup")
    second = issuer.issue_claim(recipient, "HU-DUP")
    assert first.id == second.id


def test_another_player_cannot_claim_a_rewarded_game(issuer: RewardIssuer) -> None:
    winner = Account.from_key("0x" + "55" * 32).address
    thief = Account.from_key("0x" + "66" * 32).address
    issuer.issue_claim(winner, "hu-stolen")
    with pytest.raises(RewardError):
        issuer.issue_claim(thief, "hu-stolen")


def test_nonces_are_unique(issuer: RewardIssuer) -> None:
    recipient = Account.from_key("0x" + "77" * 32).address
    nonces = {issuer.issue_claim(recipient, f"hu-{i}").nonce for i in range(25)}
    assert len(nonces) == 25


def test_unconfigured_issuer_refuses_to_sign() -> None:
    issuer = RewardIssuer(BlockchainConfig(reward_signer_private_key=""))
    with pytest.raises(RewardError):
        issuer.issue_claim(Account.from_key("0x" + "88" * 32).address, "hu-x")


def test_complete_requires_a_transaction_hash(issuer: RewardIssuer) -> None:
    recipient = Account.from_key("0x" + "99" * 32).address
    reward = issuer.issue_claim(recipient, "hu-complete")
    with pytest.raises(RewardError):
        issuer.complete(reward.id, "not-a-hash")
    completed = issuer.complete(reward.id, "0x" + "ab" * 32)
    assert completed.status.value == "Completed"
    assert completed.completed_at is not None


def test_claim_ttl_has_a_sixty_second_floor() -> None:
    config = BlockchainConfig(reward_signer_private_key=SIGNER_KEY, claim_ttl_seconds=5)
    assert config.effective_claim_ttl_seconds == 60
