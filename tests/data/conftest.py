"""Fixtures for data pipeline tests."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Repository root (contains `data/raw` and `artifacts/`)."""
    return Path(__file__).resolve().parents[2]
