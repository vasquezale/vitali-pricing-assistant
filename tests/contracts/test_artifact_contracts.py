from pathlib import Path

from vitali.contracts.artifacts import ARTIFACTS, REQUIRED_INCOME_FX_COLUMNS
from vitali.data.loaders import income_fx_csv_path


def test_canonical_artifact_relative_paths_are_stable() -> None:
    assert ARTIFACTS.income_analysis_table_fx_csv.as_posix() == "artifacts/income_analysis_table_fx.csv"
    assert (
        ARTIFACTS.income_reservations_fx_crc_sanitized_parquet.as_posix()
        == "data/sanitized/income_reservations_fx_crc_sanitized.parquet"
    )
    assert (
        ARTIFACTS.income_reservations_fx_crc_interim_parquet.as_posix()
        == "data/interim/income_reservations_fx_crc_interim.parquet"
    )
    assert ARTIFACTS.phase5_metrics_json.as_posix() == "artifacts/baseline/phase5_metrics.json"
    assert ARTIFACTS.phase6_rolling_metrics_json.as_posix() == "artifacts/evaluation/phase6_rolling_metrics.json"


def test_income_fx_required_columns_contract_is_stable() -> None:
    assert REQUIRED_INCOME_FX_COLUMNS == [
        "check_in",
        "gross_income_crc",
        "net_amount_crc",
        "unit_id",
        "currency",
    ]


def test_loaders_income_fx_path_uses_canonical_contract(tmp_path: Path) -> None:
    expected = tmp_path / ARTIFACTS.income_analysis_table_fx_csv
    assert income_fx_csv_path(tmp_path) == expected

