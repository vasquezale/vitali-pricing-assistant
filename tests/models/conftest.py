"""Fixtures for model tests."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Repository root."""
    return Path(__file__).resolve().parents[2]
