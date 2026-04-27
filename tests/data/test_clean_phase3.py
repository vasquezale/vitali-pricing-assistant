"""Tests for Phase 3 cleaning invariants (Yellow gate)."""

from pathlib import Path

import pytest

from vitali.data.clean import prepare_expenses, prepare_income_from_raw_airbnb, write_phase3_outputs
from vitali.data.loaders import income_fx_csv_path


def test_prepare_income_splits_resolution_payments(repo_root: Path) -> None:
    raw_path = repo_root / "data" / "raw" / "airbnb" / "Ingresos_Vitali_ingresos_anonimizados.csv"
    fx_path = income_fx_csv_path(repo_root)
    if not raw_path.is_file() or not fx_path.is_file():
        pytest.skip("raw airbnb income or fx table not present")

    prepared = prepare_income_from_raw_airbnb(repo_root)
    assert "record_type" in prepared.reservations_fx_crc.columns
    assert set(prepared.reservations_fx_crc["record_type"].dropna().unique()) <= {"reservation"}
    assert set(prepared.ledger_resolution_payments["record_type"].dropna().unique()) <= {"resolution_payment"}


def test_prepare_income_has_safe_calendar_features(repo_root: Path) -> None:
    raw_path = repo_root / "data" / "raw" / "airbnb" / "Ingresos_Vitali_ingresos_anonimizados.csv"
    fx_path = income_fx_csv_path(repo_root)
    if not raw_path.is_file() or not fx_path.is_file():
        pytest.skip("raw airbnb income or fx table not present")

    prepared = prepare_income_from_raw_airbnb(repo_root)
    df = prepared.reservations_fx_crc
    for col in ["check_in_year", "check_in_month", "check_in_dow", "is_weekend"]:
        assert col in df.columns
    assert df["is_weekend"].dropna().isin([0, 1]).all()


def test_prepare_income_preserves_currency_and_uses_crc_columns(repo_root: Path) -> None:
    raw_path = repo_root / "data" / "raw" / "airbnb" / "Ingresos_Vitali_ingresos_anonimizados.csv"
    fx_path = income_fx_csv_path(repo_root)
    if not raw_path.is_file() or not fx_path.is_file():
        pytest.skip("raw airbnb income or fx table not present")

    prepared = prepare_income_from_raw_airbnb(repo_root)
    df = prepared.reservations_fx_crc
    assert "currency" in df.columns
    assert "gross_income_crc" in df.columns
    assert df["gross_income_crc"].notna().any()
    dup_merge = [c for c in df.columns if c.endswith("_x") or c.endswith("_y")]
    assert not dup_merge, f"unexpected merge suffix columns: {dup_merge}"
    assert "booking_lead_days" in df.columns


def test_write_phase3_outputs_includes_interim_reservations(repo_root: Path) -> None:
    raw_path = repo_root / "data" / "raw" / "airbnb" / "Ingresos_Vitali_ingresos_anonimizados.csv"
    fx_path = repo_root / "artifacts" / "income_analysis_table_fx.csv"
    if not raw_path.is_file() or not fx_path.is_file():
        pytest.skip("raw airbnb income or fx table not present")

    prepared = prepare_income_from_raw_airbnb(repo_root)
    expenses = prepare_expenses(repo_root, years=(2025,))
    paths = write_phase3_outputs(prepared, expenses, root=repo_root)
    interim_res = paths.get("income_reservations_fx_crc_interim")
    assert interim_res is not None
    assert interim_res.is_file()


def test_prepare_expenses_adds_bucket(repo_root: Path) -> None:
    x2025 = repo_root / "data" / "raw" / "2025" / "expenses_2025_raw.xlsx"
    if not x2025.is_file():
        pytest.skip("expense workbook not present")

    df = prepare_expenses(repo_root, years=(2025,))
    assert "expense_bucket" in df.columns
    assert set(df["expense_bucket"].dropna().unique()) <= {"operativo_defendible", "ambiguo", "posible_capex"}

