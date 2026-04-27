"""Tests for `validate_pipeline_inputs` branches."""

import pandas as pd

from vitali.data.validators import validate_pipeline_inputs


def test_validate_missing_columns() -> None:
    exp = pd.DataFrame({"wrong": [1]})
    inc = pd.DataFrame({"check_in": pd.to_datetime(["2025-01-01"]), "gross_income_crc": [1.0]})
    r = validate_pipeline_inputs(exp, inc)
    assert not r.is_valid
    assert any("Expenses missing" in e for e in r.errors)


def test_validate_income_missing_column() -> None:
    exp = pd.DataFrame({"fecha": pd.to_datetime(["2025-01-01"]), "monto_crc": [10.0]})
    inc = pd.DataFrame({"check_in": pd.to_datetime(["2025-01-01"])})
    r = validate_pipeline_inputs(exp, inc)
    assert not r.is_valid
    assert any("Income missing" in e for e in r.errors)


def test_validate_all_null_amounts() -> None:
    exp = pd.DataFrame({"fecha": pd.to_datetime(["2025-01-01"]), "monto_crc": [float("nan")]})
    inc = pd.DataFrame({"check_in": pd.to_datetime(["2025-01-01"]), "gross_income_crc": [1.0]})
    r = validate_pipeline_inputs(exp, inc)
    assert not r.is_valid
    assert any("All expense amounts" in e for e in r.errors)


def test_validate_negative_expense_alert() -> None:
    exp = pd.DataFrame({"fecha": pd.to_datetime(["2025-01-01", "2025-02-01"]), "monto_crc": [10.0, -1.0]})
    inc = pd.DataFrame(
        {
            "check_in": pd.to_datetime(["2025-06-01", "2025-06-02"]),
            "gross_income_crc": [100.0, 200.0],
            "check_in_year": [2025, 2025],
            "check_in_month": [6, 6],
        }
    )
    r = validate_pipeline_inputs(exp, inc, low_booking_threshold=1)
    assert r.is_valid
    assert any("negative monto_crc" in a for a in r.alerts)


def test_validate_null_fecha_alert() -> None:
    exp = pd.DataFrame({"fecha": pd.to_datetime([pd.NaT]), "monto_crc": [10.0]})
    inc = pd.DataFrame(
        {
            "check_in": pd.to_datetime(["2025-06-01"]),
            "gross_income_crc": [100.0],
            "check_in_year": [2025],
            "check_in_month": [6],
        }
    )
    r = validate_pipeline_inputs(exp, inc, low_booking_threshold=1)
    assert r.is_valid
    assert any("null fecha" in a for a in r.alerts)


def test_validate_null_check_in_alert() -> None:
    exp = pd.DataFrame({"fecha": pd.to_datetime(["2025-01-01"]), "monto_crc": [10.0]})
    inc = pd.DataFrame(
        {
            "check_in": pd.to_datetime([pd.NaT]),
            "gross_income_crc": [100.0],
            "check_in_year": [2025],
            "check_in_month": [1],
        }
    )
    r = validate_pipeline_inputs(exp, inc, low_booking_threshold=1)
    assert r.is_valid
    assert any("null check_in" in a for a in r.alerts)
