"""Tests for `vitali.data.loaders`."""

from pathlib import Path

import pytest

from vitali.data.loaders import (
    expenses_workbook_path,
    load_expenses,
    load_income_fx,
    project_root,
)


def test_project_root_explicit(tmp_path: Path) -> None:
    assert project_root(tmp_path) == tmp_path.resolve()


@pytest.mark.skipif(
    not expenses_workbook_path(2025).is_file(),
    reason="2025 expense workbook not present",
)
def test_load_expenses_2025(repo_root: Path) -> None:
    df = load_expenses(2025, repo_root)
    assert len(df) > 100
    assert "monto_crc" in df.columns
    assert df["monto_crc"].sum() > 0


@pytest.mark.skipif(
    not expenses_workbook_path(2026).is_file(),
    reason="2026 expense workbook not present",
)
def test_load_expenses_2026(repo_root: Path) -> None:
    df = load_expenses(2026, repo_root)
    assert len(df) > 10
    assert df["fecha"].dt.year.max() <= 2026


def test_load_income_fx(repo_root: Path) -> None:
    path = repo_root / "artifacts" / "income_analysis_table_fx.csv"
    if not path.is_file():
        pytest.skip("income FX table not present")
    df = load_income_fx(repo_root, min_check_in_year=2025)
    assert len(df) >= 100
    assert df["gross_income_crc"].sum() > 1_000_000
    assert df["check_in_year"].min() >= 2025
