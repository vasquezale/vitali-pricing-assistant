"""Error-path tests for loaders."""

from pathlib import Path

import pytest

from vitali.data.loaders import expense_config_for_year, load_expenses, load_income_fx, project_root


def test_expense_config_unsupported_year() -> None:
    with pytest.raises(ValueError, match="Unsupported expense year"):
        expense_config_for_year(2024)


def test_load_expenses_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Expense workbook not found"):
        load_expenses(2025, tmp_path)


def test_load_income_fx_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Income FX table not found"):
        load_income_fx(tmp_path)


def test_load_income_fx_missing_columns(tmp_path: Path) -> None:
    p = tmp_path / "artifacts"
    p.mkdir(parents=True)
    bad = p / "income_analysis_table_fx.csv"
    bad.write_text("check_in,gross_income_crc\n2025-01-01,100\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        load_income_fx(tmp_path, min_check_in_year=None)


def test_load_income_fx_no_year_filter(tmp_path: Path, repo_root: Path) -> None:
    src = repo_root / "artifacts" / "income_analysis_table_fx.csv"
    if not src.is_file():
        pytest.skip("income FX not present")
    dest = tmp_path / "artifacts"
    dest.mkdir(parents=True)
    dest.joinpath("income_analysis_table_fx.csv").write_bytes(src.read_bytes())
    df = load_income_fx(tmp_path, min_check_in_year=None)
    assert df["check_in_year"].min() < 2025


def test_project_root_default_uses_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    assert project_root() == tmp_path.resolve()
