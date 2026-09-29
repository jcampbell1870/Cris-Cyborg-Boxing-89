"""Configuration for the Python 3 rewrite of Cris Cyborg Boxing 89.

The Arcade1870 (ARC / A1870) reward settings intentionally mirror Crypto
Hockey so both games share the *same* payout system and the *same* deployed
``Arcade1870RewardVault`` treasury contract. Do not deploy a second vault for
this game - reuse the existing address.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal

# Arcade1870 (ARC / A1870) ERC-20 token on Ethereum mainnet - identical to the
# address configured by Crypto Hockey and Crypto Chess.
DEFAULT_TOKEN_ADDRESS = "0x8eddD4edea39c5B5f77662453600F53A202EE47C"

# Shared, pre-funded Arcade1870RewardVault treasury. Chain- and consumer
# agnostic: the same vault backs Crypto Chess, Crypto Hockey and this game.
DEFAULT_REWARD_VAULT_ADDRESS = "0x1e4f6e4a382adbdb662733a19ae773d3ab8f497d"

DEFAULT_RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY"

# EIP-712 domain verified on-chain by Arcade1870RewardVault.
VAULT_DOMAIN_NAME = "Arcade1870RewardVault"
VAULT_DOMAIN_VERSION = "1"

TOKEN_SYMBOL = "A1870"


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_decimal(name: str, default: Decimal) -> Decimal:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return Decimal(raw)
    except ArithmeticError:
        return default


@dataclass
class BlockchainConfig:
    """Arcade1870 reward configuration (same values as Crypto Hockey)."""

    rpc_url: str = DEFAULT_RPC_URL
    token_address: str = DEFAULT_TOKEN_ADDRESS
    reward_vault_address: str = DEFAULT_REWARD_VAULT_ADDRESS

    #: Private key of the dedicated reward signer. It never has custody of ARC;
    #: it can only authorize claims against the vault. Provide it through the
    #: ``REWARD_SIGNER_PRIVATE_KEY`` environment variable / secrets manager -
    #: never commit it to source control.
    reward_signer_private_key: str = ""

    chain_id: int = 1
    chain_name: str = "Ethereum Mainnet"
    supported_chain_ids: tuple[int, ...] = (1, 11155111, 137)

    #: Flat ARC payout per completed game, exactly as in Crypto Hockey.
    reward_amount: Decimal = Decimal("10")
    token_decimals: int = 18

    #: How long an issued claim signature stays valid, in seconds (min 60).
    claim_ttl_seconds: int = 600

    @classmethod
    def from_env(cls) -> "BlockchainConfig":
        return cls(
            rpc_url=_env_str("ETHEREUM_RPC_URL", DEFAULT_RPC_URL),
            token_address=_env_str("ARCADE1870_TOKEN_ADDRESS", DEFAULT_TOKEN_ADDRESS),
            reward_vault_address=_env_str(
                "REWARD_VAULT_ADDRESS", DEFAULT_REWARD_VAULT_ADDRESS
            ),
            reward_signer_private_key=_env_str("REWARD_SIGNER_PRIVATE_KEY", ""),
            chain_id=_env_int("CHAIN_ID", 1),
            reward_amount=_env_decimal("REWARD_AMOUNT", Decimal("10")),
            token_decimals=_env_int("TOKEN_DECIMALS", 18),
            claim_ttl_seconds=_env_int("CLAIM_TTL_SECONDS", 600),
        )

    @property
    def effective_claim_ttl_seconds(self) -> int:
        """Claim lifetime with the same 60 second floor Crypto Hockey uses."""
        return max(60, self.claim_ttl_seconds)

    @property
    def reward_amount_wei(self) -> int:
        return int(self.reward_amount * (Decimal(10) ** self.token_decimals))

    @property
    def is_configured(self) -> bool:
        return bool(self.reward_vault_address and self.reward_signer_private_key)


@dataclass
class ServerConfig:
    """Settings for the FastAPI match/tournament server."""

    host: str = "0.0.0.0"
    port: int = 8000
    jwt_secret: str = field(default_factory=lambda: _env_str("JWT_SECRET", ""))
    jwt_issuer: str = "CrisCyborgBoxing"
    jwt_audience: str = "CrisCyborgBoxingClients"
    jwt_expiry_minutes: int = 1440

    #: GG Poker style sit-and-go tournaments seat exactly eight players.
    tournament_seat_limit: int = 8

    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls(
            host=_env_str("HOST", "0.0.0.0"),
            port=_env_int("PORT", 8000),
            jwt_secret=_env_str("JWT_SECRET", ""),
            jwt_expiry_minutes=_env_int("JWT_EXPIRY_MINUTES", 1440),
            tournament_seat_limit=_env_int("TOURNAMENT_SEAT_LIMIT", 8),
        )
