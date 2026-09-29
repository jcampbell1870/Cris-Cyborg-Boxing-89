"""Wallet-based session tokens (JWT) for the online services."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

import jwt

from .config import ServerConfig
from .wallet import generate_auth_message, normalize_address, verify_signature

ALGORITHM = "HS256"
#: How long a login challenge stays valid, in seconds.
CHALLENGE_TTL_SECONDS = 300


class AuthError(Exception):
    """Raised when a login or token check fails."""


@dataclass
class Challenge:
    address: str
    message: str
    issued_at: float


class AuthService:
    """Issues sign-in challenges and JWT session tokens."""

    def __init__(self, config: ServerConfig | None = None) -> None:
        self.config = config or ServerConfig.from_env()
        if not self.config.jwt_secret:
            # A random per-process secret keeps local development usable while
            # ensuring tokens are never signed with a hardcoded value.
            self.config.jwt_secret = secrets.token_urlsafe(48)
        self._challenges: dict[str, Challenge] = {}

    def create_challenge(self, address: str) -> Challenge:
        address = normalize_address(address)
        challenge = Challenge(
            address=address, message=generate_auth_message(), issued_at=time.time()
        )
        self._challenges[address.lower()] = challenge
        return challenge

    def login(self, address: str, signature: str) -> str:
        """Verify the signed challenge and return a session token."""
        address = normalize_address(address)
        challenge = self._challenges.get(address.lower())
        if challenge is None:
            raise AuthError("Request a sign-in message first.")
        if time.time() - challenge.issued_at > CHALLENGE_TTL_SECONDS:
            self._challenges.pop(address.lower(), None)
            raise AuthError("The sign-in message expired, request a new one.")
        if not verify_signature(address, challenge.message, signature):
            raise AuthError("Signature verification failed.")
        # A challenge is single use so a captured signature cannot be replayed.
        self._challenges.pop(address.lower(), None)
        return self.issue_token(address)

    def issue_token(self, address: str) -> str:
        issued_at = int(time.time())
        payload = {
            "sub": normalize_address(address),
            "iss": self.config.jwt_issuer,
            "aud": self.config.jwt_audience,
            "iat": issued_at,
            "exp": issued_at + self.config.jwt_expiry_minutes * 60,
        }
        return jwt.encode(payload, self.config.jwt_secret, algorithm=ALGORITHM)

    def address_from_token(self, token: str) -> str:
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[ALGORITHM],
                audience=self.config.jwt_audience,
                issuer=self.config.jwt_issuer,
            )
        except jwt.PyJWTError as exc:
            raise AuthError("Invalid or expired session token.") from exc
        address = payload.get("sub")
        if not address:
            raise AuthError("Session token is missing a wallet address.")
        return address
