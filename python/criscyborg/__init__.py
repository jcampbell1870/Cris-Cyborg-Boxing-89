"""Cris Cyborg Boxing - Python 3 rewrite.

A 2D boxing game with online one-vs-one bouts, GG Poker style eight-max
sit-and-go tournaments, and Arcade1870 (ARC) play-to-earn rewards paid from
the shared Arcade1870RewardVault treasury used by Crypto Hockey.
"""

from .config import BlockchainConfig, ServerConfig
from .online import LobbyError, OnlineCompetitionService
from .rewards import RewardError, RewardIssuer

__all__ = [
    "BlockchainConfig",
    "ServerConfig",
    "OnlineCompetitionService",
    "LobbyError",
    "RewardIssuer",
    "RewardError",
]

__version__ = "1.0.0"
