"""Arcade1870 (ARC / A1870) reward payout system.

This is a direct port of the Crypto Hockey / Crypto Chess payout flow:

1. A completed game makes the backend issue a reward for the winner.
2. The backend signs an EIP-712 ``Claim(address recipient, uint256 amount,
   uint256 nonce, uint256 deadline)`` message with a dedicated reward-signer
   key - it never transfers ARC itself and never has custody of funds.
3. The player submits ``claim(amount, nonce, deadline, signature)`` to the
   shared, pre-funded ``Arcade1870RewardVault`` treasury contract from their
   own wallet, paying their own gas, and receives ARC directly.
4. The client reports the resulting transaction hash back so the backend can
   record the completed payout.

The vault is the *same* deployed treasury used by Crypto Hockey - see
``config.DEFAULT_REWARD_VAULT_ADDRESS``.
"""

from __future__ import annotations

import itertools
import threading
import time
from decimal import Decimal

from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import to_checksum_address

from .config import (
    TOKEN_SYMBOL,
    VAULT_DOMAIN_NAME,
    VAULT_DOMAIN_VERSION,
    BlockchainConfig,
)
from .models import Reward, RewardStatus, new_id

CLAIM_TYPE = {
    "Claim": [
        {"name": "recipient", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
        {"name": "deadline", "type": "uint256"},
    ]
}


class RewardError(Exception):
    """Raised when a reward claim cannot be issued."""


class RewardIssuer:
    """Issues and tracks signed Arcade1870RewardVault claims."""

    def __init__(self, config: BlockchainConfig | None = None) -> None:
        self.config = config or BlockchainConfig.from_env()
        self._lock = threading.Lock()
        self._nonce_counter = itertools.count(1)
        #: game id -> reward, so a game can only ever be rewarded once.
        self._claims_by_game: dict[str, Reward] = {}
        self._rewards: dict[str, Reward] = {}

    # ------------------------------------------------------------------
    # Issuing
    # ------------------------------------------------------------------
    def issue_claim(self, recipient: str, game_id: str) -> Reward:
        """Issue a signed vault claim for ``recipient`` for ``game_id``.

        The amount is always resolved server-side from configuration (a flat
        payout per completed game, as in Crypto Hockey); a client-supplied
        amount is never trusted.
        """
        if not self.config.is_configured:
            raise RewardError(
                "Arcade1870RewardVault is not configured "
                "(missing vault address or reward signer key)."
            )

        normalized_game_id = (game_id or "").strip().lower()
        if not normalized_game_id:
            raise RewardError("A game id is required to issue a reward claim.")

        recipient = self._normalize_recipient(recipient)

        with self._lock:
            existing = self._claims_by_game.get(normalized_game_id)
            if existing is not None:
                if existing.recipient.lower() != recipient.lower():
                    raise RewardError("This completed game has already been rewarded.")
                if existing.deadline > int(time.time()):
                    return existing
                # The previous claim expired unused - re-issue a fresh one
                # bound to the same recipient and game.
                reward = self._sign_reward(recipient, normalized_game_id)
                self._claims_by_game[normalized_game_id] = reward
                self._rewards[reward.id] = reward
                return reward

            reward = self._sign_reward(recipient, normalized_game_id)
            self._claims_by_game[normalized_game_id] = reward
            self._rewards[reward.id] = reward
            return reward

    def _sign_reward(self, recipient: str, game_id: str) -> Reward:
        cfg = self.config
        amount_wei = cfg.reward_amount_wei
        if amount_wei <= 0:
            raise RewardError("Configured reward amount must be greater than zero.")

        nonce = self._next_nonce()
        deadline = int(time.time()) + cfg.effective_claim_ttl_seconds
        vault_address = to_checksum_address(cfg.reward_vault_address)

        signature = self.sign_claim(
            recipient=recipient,
            amount_wei=amount_wei,
            nonce=nonce,
            deadline=deadline,
        )

        return Reward(
            id=new_id("rwd", 12),
            recipient=recipient,
            amount=Decimal(cfg.reward_amount),
            amount_wei=amount_wei,
            nonce=nonce,
            deadline=deadline,
            signature=signature,
            vault_address=vault_address,
            token_address=to_checksum_address(cfg.token_address),
            chain_id=cfg.chain_id,
            token_symbol=TOKEN_SYMBOL,
            token_decimals=cfg.token_decimals,
            game_id=game_id,
            status=RewardStatus.ISSUED,
        )

    def _next_nonce(self) -> int:
        # Same scheme as Crypto Hockey: millisecond timestamp with a
        # monotonic counter suffix, so nonces never collide per recipient.
        return int(time.time() * 1000) * 1000 + next(self._nonce_counter)

    @staticmethod
    def _normalize_recipient(recipient: str) -> str:
        try:
            return to_checksum_address(recipient)
        except (ValueError, TypeError) as exc:
            raise RewardError(f"Invalid recipient address: {recipient!r}") from exc

    # ------------------------------------------------------------------
    # Signing primitives
    # ------------------------------------------------------------------
    def typed_data(
        self, recipient: str, amount_wei: int, nonce: int, deadline: int
    ) -> dict:
        """Build the EIP-712 payload the vault verifies on-chain."""
        return {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                **CLAIM_TYPE,
            },
            "primaryType": "Claim",
            "domain": {
                "name": VAULT_DOMAIN_NAME,
                "version": VAULT_DOMAIN_VERSION,
                "chainId": self.config.chain_id,
                "verifyingContract": to_checksum_address(
                    self.config.reward_vault_address
                ),
            },
            "message": {
                "recipient": to_checksum_address(recipient),
                "amount": amount_wei,
                "nonce": nonce,
                "deadline": deadline,
            },
        }

    def sign_claim(
        self, recipient: str, amount_wei: int, nonce: int, deadline: int
    ) -> str:
        payload = self.typed_data(recipient, amount_wei, nonce, deadline)
        signable = encode_typed_data(full_message=payload)
        signed = Account.from_key(self.config.reward_signer_private_key).sign_message(
            signable
        )
        return signed.signature.to_0x_hex()

    def recover_signer(self, reward: Reward) -> str:
        """Recover the signer address of an issued claim (used by tests)."""
        payload = self.typed_data(
            reward.recipient, reward.amount_wei, reward.nonce, reward.deadline
        )
        return Account.recover_message(
            encode_typed_data(full_message=payload), signature=reward.signature
        )

    @property
    def signer_address(self) -> str:
        if not self.config.reward_signer_private_key:
            raise RewardError("No reward signer key configured.")
        return Account.from_key(self.config.reward_signer_private_key).address

    # ------------------------------------------------------------------
    # Bookkeeping
    # ------------------------------------------------------------------
    def complete(self, reward_id: str, transaction_hash: str) -> Reward:
        with self._lock:
            reward = self._rewards.get(reward_id)
            if reward is None:
                raise RewardError(f"Unknown reward {reward_id!r}.")
            tx_hash = (transaction_hash or "").strip()
            if not _is_tx_hash(tx_hash):
                raise RewardError("A valid 0x-prefixed transaction hash is required.")
            reward.transaction_hash = tx_hash
            reward.status = RewardStatus.COMPLETED
            reward.completed_at = time.time()
            return reward

    def get(self, reward_id: str) -> Reward | None:
        return self._rewards.get(reward_id)

    def for_recipient(self, address: str) -> list[Reward]:
        low = (address or "").lower()
        return sorted(
            (r for r in self._rewards.values() if r.recipient.lower() == low),
            key=lambda r: r.created_at,
            reverse=True,
        )

    def for_game(self, game_id: str) -> Reward | None:
        return self._claims_by_game.get((game_id or "").strip().lower())


def _is_tx_hash(value: str) -> bool:
    if not value.startswith("0x") or len(value) != 66:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
