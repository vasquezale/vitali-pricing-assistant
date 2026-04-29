from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from vitali.mvp.monthly_balance import (
    INCOME_PROJECTION_PATH,
    MONTHLY_BALANCE_PATH,
    PROHIBITED_TERMS,
    MonthlyBalanceError,
    evaluate_historical_balance,
    load_income_projection,
    load_monthly_balance,
    project_monthly_balance,
)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_load_monthly_balance_dataset_contract(repo_root: Path) -> None:
    df = load_monthly_balance(repo_root=repo_root)
    assert not df.empty
    assert sorted(df["year"].dropna().astype(int).unique().tolist()) == [2024, 2025, 2026]
    assert set(df["month"].dropna().astype(int).tolist()).issuperset({1, 2, 3, 12})


def test_load_income_projection_contract(repo_root: Path) -> None:
    projection = load_income_projection(repo_root=repo_root)
    assert len(projection["projections"]) == 3
    assert projection["currency"] == "CRC"


def test_evaluate_historical_balance_valid_ok_month(repo_root: Path) -> None:
    result = evaluate_historical_balance(2025, 10, "wide", repo_root=repo_root)
    assert result["income_type"] == "historical"
    assert result["scenario"] == "wide"
    assert result["gross_income_crc"] > 0
    assert result["expense_estimated_crc"] is not None
    assert result["balance_estimated_crc"] is not None
    assert result["data_quality_flag"] == "ok"


def test_evaluate_historical_balance_renovation_month_warns(repo_root: Path) -> None:
    result = evaluate_historical_balance(2026, 2, "medium", repo_root=repo_root)
    assert result["is_renovation_month"] is True
    assert result["has_estimated_scenario"] is False
    assert any("remodelación" in warning or "remodelacion" in warning for warning in result["warnings"])


@pytest.mark.parametrize(
    ("year", "month", "scenario"),
    [
        (1999, 1, "conservative"),
        (2025, 13, "conservative"),
        (2025, 1, "aggressive"),
    ],
)
def test_evaluate_historical_balance_invalid_inputs_raise(
    repo_root: Path,
    year: int,
    month: int,
    scenario: str,
) -> None:
    with pytest.raises(MonthlyBalanceError):
        evaluate_historical_balance(year, month, scenario, repo_root=repo_root)


def test_load_monthly_balance_rejects_missing_columns(tmp_path: Path) -> None:
    broken = pd.DataFrame([{"year": 2025, "month": 1, "ingresos_gross_crc": 1000.0}])
    dataset_path = tmp_path / "broken.parquet"
    broken.to_parquet(dataset_path, index=False)
    with pytest.raises(MonthlyBalanceError, match="Faltan columnas requeridas"):
        load_monthly_balance(dataset_path=dataset_path)


def test_project_monthly_balance_returns_next_three_months(repo_root: Path) -> None:
    projection = project_monthly_balance("conservative", repo_root=repo_root)
    assert len(projection) == 3
    assert all(item["income_type"] == "projected" for item in projection)
    assert all(item["estimated_expense_crc"] is not None for item in projection)


def test_projected_messages_avoid_prohibited_language(repo_root: Path) -> None:
    projection = project_monthly_balance("wide", repo_root=repo_root)
    for item in projection:
        lowered = item["message"].lower()
        for term in PROHIBITED_TERMS:
            assert term not in lowered


def test_historical_message_avoids_prohibited_language(repo_root: Path) -> None:
    result = evaluate_historical_balance(2025, 5, "conservative", repo_root=repo_root)
    lowered = result["message"].lower()
    for term in PROHIBITED_TERMS:
        assert term not in lowered


def test_contract_paths_are_stable() -> None:
    assert MONTHLY_BALANCE_PATH.as_posix() == "data/processed/f7_capa2_monthly_balance.parquet"
    assert INCOME_PROJECTION_PATH.as_posix() == "artifacts/mvp/capa1_income_projection.json"
