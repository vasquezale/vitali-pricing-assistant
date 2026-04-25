"""Shared fixtures for Proyecto Vitali tests."""

import pandas as pd
import pytest

from vitali.config import Config


@pytest.fixture(scope="session")
def config() -> Config:
    """Load project configuration."""
    return Config.from_yaml()


@pytest.fixture()
def sample_reservations() -> pd.DataFrame:
    """Synthetic reservation data for testing (no PII)."""
    return pd.DataFrame(
        {
            "check_in": pd.to_datetime(
                ["2024-01-15", "2024-02-20", "2024-03-10", "2024-07-05", "2024-08-01", "2024-12-20"]
            ),
            "check_out": pd.to_datetime(
                ["2024-01-18", "2024-02-23", "2024-03-14", "2024-07-08", "2024-08-04", "2024-12-25"]
            ),
            "nights": [3, 3, 4, 3, 3, 5],
            "nightly_rate": [50.0, 55.0, 70.0, 40.0, 80.0, 90.0],
            "total_price": [150.0, 165.0, 280.0, 120.0, 240.0, 450.0],
            "status": ["confirmed", "confirmed", "confirmed", "confirmed", "confirmed", "confirmed"],
        }
    )
