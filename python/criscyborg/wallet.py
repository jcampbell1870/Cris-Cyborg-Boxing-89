"""MetaMask wallet authentication helpers.

Players are identified by their wallet address; they prove ownership by
signing a nonce message with ``personal_sign`` (EIP-191), exactly as in the
C# ``MetaMaskService`` this module replaces.
"""

from __future__ import annotations

import re
import secrets
import time

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def is_valid_address(address: str) -> bool:
    return bool(address) and bool(_ADDRESS_RE.match(address))


def normalize_address(address: str) -> str:
    if not is_valid_address(address):
        raise ValueError(f"Invalid wallet address: {address!r}")
    return to_checksum_address(address)


def generate_auth_message(nonce: str | None = None) -> str:
    """Build the message a player signs to log in."""
    nonce = nonce or secrets.token_hex(16)
    return (
        "Welcome to Cris Cyborg Boxing 89!\n\n"
        "Sign this message to verify your wallet. "
        "This request will not trigger a blockchain transaction "
        "or cost any gas.\n\n"
        f"Nonce: {nonce}\n"
        f"Issued at: {int(time.time())}"
    )


def verify_signature(address: str, message: str, signature: str) -> bool:
    """Return ``True`` if ``signature`` over ``message`` came from ``address``."""
    if not address or not message or not signature:
        return False
    try:
        recovered = Account.recover_message(
            encode_defunct(text=message), signature=signature
        )
    except Exception:
        return False
    return recovered.lower() == address.lower()


def short_address(address: str) -> str:
    """``0x1234...abcd`` style display fallback used by the lobby."""
    if not is_valid_address(address):
        return "unknown"
    return f"{address[:6]}...{address[-4:]}"


def display_name(address: str, requested: str | None) -> str:
    """Trim a requested alias to 24 characters, falling back to the address."""
    alias = (requested or "").strip()
    if not alias:
        return short_address(address)
    return alias[:24]
