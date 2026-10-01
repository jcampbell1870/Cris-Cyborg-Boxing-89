from __future__ import annotations

import argparse

import pytest

from criscyborg.client.pygame_client import parse_resolution


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("960x540", (960, 540)),
        ("2560x1440", (2560, 1440)),
        ("3840x2160", (3840, 2160)),
    ],
)
def test_parse_resolution(value: str, expected: tuple[int, int]) -> None:
    assert parse_resolution(value) == expected


@pytest.mark.parametrize("value", ["nope", "1920", "800x600", "7681x4320", "960x4321"])
def test_parse_resolution_rejects_unsupported_values(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_resolution(value)
