"""Tests for validation and monthly reconciliation."""

from pathlib import Path

import pandas as pd
import pytest

from vitali.data import pipeline as pipeline_mod
from vitali.data.loaders import load_expenses, load_income_fx
from vitali.data.pipeline import load_validate_reconcile, reconcile_monthly
from vitali.data.validators import DataQualityReport, validate_pipeline_inputs


def test_validate_pipeline_inputs_ok(repo_root: Path) -> None:
    exp_path = repo_root / "data" / "raw" / "2025" / "expenses_2025_raw.xlsx"
    inc_path = repo_root / "artifacts" / "income_analysis_table_fx.csv"
    if not exp_path.is_file() or not inc_path.is_file():
        pytest.skip("raw data or income FX not present")
    exp = load_expenses(2025, repo_root)
    inc = load_income_fx(repo_root, min_check_in_year=2025)
    report = validate_pipeline_inputs(exp, inc)
    assert report.is_valid
    assert not report.errors


def test_reconcile_monthly_shape(repo_root: Path) -> None:
    exp_path = repo_root / "data" / "raw" / "2025" / "expenses_2025_raw.xlsx"
    inc_path = repo_root / "artifacts" / "income_analysis_table_fx.csv"
    if not exp_path.is_file() or not inc_path.is_file():
        pytest.skip("raw data or income FX not present")
    exp = load_expenses(2025, repo_root)
    inc = load_income_fx(repo_root, min_check_in_year=2025)
    recon = reconcile_monthly(exp, inc)
    assert not recon.empty
    assert "neto_gross_menos_egresos_crc" in recon.columns
    assert recon["neto_gross_menos_egresos_crc"].notna().all()


def test_reconcile_identity_per_row(repo_root: Path) -> None:
    """neto = ingresos_gross - egresos for each period (within float tolerance)."""
    exp_path = repo_root / "data" / "raw" / "2025" / "expenses_2025_raw.xlsx"
    inc_path = repo_root / "artifacts" / "income_analysis_table_fx.csv"
    if not exp_path.is_file() or not inc_path.is_file():
        pytest.skip("raw data or income FX not present")
    exp = load_expenses(2025, repo_root)
    inc = load_income_fx(repo_root, min_check_in_year=2025)
    recon = reconcile_monthly(exp, inc)
    expected = recon["ingresos_gross_crc"] - recon["egresos_crc"]
    pd.testing.assert_series_equal(
        recon["neto_gross_menos_egresos_crc"],
        expected,
        check_names=False,
    )


def test_load_validate_reconcile_end_to_end(repo_root: Path) -> None:
    if not (repo_root / "data" / "raw" / "2025" / "expenses_2025_raw.xlsx").is_file():
        pytest.skip("raw data not present")
    _, _, report, recon = load_validate_reconcile(repo_root)
    assert report.is_valid
    assert isinstance(recon, pd.DataFrame)
    assert len(recon) >= 12


def test_validate_flags_low_bookings_synthetic() -> None:
    exp = pd.DataFrame({"fecha": pd.to_datetime(["2025-08-01"]), "monto_crc": [100.0]})
    inc = pd.DataFrame(
        {
            "check_in": pd.to_datetime(["2025-08-02"]),
            "gross_income_crc": [50.0],
            "net_amount_crc": [40.0],
            "unit_id": ["room_a"],
            "currency": ["CRC"],
            "check_in_year": [2025],
            "check_in_month": [8],
        }
    )
    report = validate_pipeline_inputs(exp, inc, low_booking_threshold=5)
    assert report.is_valid
    assert any("Low booking count" in a for a in report.alerts)


def test_load_validate_reconcile_empty_recon_when_validation_fails(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not (repo_root / "data" / "raw" / "2025" / "expenses_2025_raw.xlsx").is_file():
        pytest.skip("raw data not present")

    def _invalid(*_args, **_kwargs) -> DataQualityReport:
        return DataQualityReport(is_valid=False, errors=["forced failure"], alerts=[])

    monkeypatch.setattr(pipeline_mod, "validate_pipeline_inputs", _invalid)
    _, _, report, recon = load_validate_reconcile(repo_root)
    assert not report.is_valid
    assert recon.empty
