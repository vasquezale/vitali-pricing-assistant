import pandas as pd
import pytest

from vitali.config import Config
from vitali.contracts.artifacts import ARTIFACTS, REQUIRED_INCOME_FX_COLUMNS
from vitali.data.fx_rates import resolve_fx_rates_to_crc
from vitali.data.fx_table import build_income_analysis_table_fx


@pytest.fixture()
def sample_income_csv(tmp_path):
    frame = pd.DataFrame(
        {
            "record_type": ["reservation", "reservation"],
            "movement_date": ["2026-01-05", "2026-01-06"],
            "booking_date": ["2025-12-20", "2025-12-22"],
            "check_in": ["2026-01-10", "2026-01-12"],
            "check_out": ["2026-01-11", "2026-01-14"],
            "nights": [1, 2],
            "unit_id": ["room_a", "room_b"],
            "currency": ["USD", "CRC"],
            "net_amount": [120.0, 180000.0],
            "service_fee": [4.0, 6000.0],
            "quick_pay_fee": [None, None],
            "cleaning_fee": [20.0, 0.0],
            "gross_income": [124.0, 186000.0],
            "lodging_tax": [0.0, 0.0],
            "income_year": [2026, 2026],
            "booking_lead_days": [21, 21],
        }
    )
    path = tmp_path / "income.csv"
    frame.to_csv(path, index=False)
    return path


def test_fx_producer_writes_canonical_csv_and_schema(tmp_path, sample_income_csv):
    # Minimal config is fine; we override input_csv explicitly.
    config = Config()
    out = build_income_analysis_table_fx(
        repo_root=tmp_path,
        input_csv=sample_income_csv,
        config=config,
        fx_rates_to_crc={"USD": 510.0, "CRC": 1.0},
        output_csv=ARTIFACTS.income_analysis_table_fx_csv,
    )
    assert out == (tmp_path / ARTIFACTS.income_analysis_table_fx_csv)
    df = pd.read_csv(out)
    for col in REQUIRED_INCOME_FX_COLUMNS:
        assert col in df.columns
    assert df["gross_income_crc"].notna().all()
    assert set(df["fx_normalization_status"].unique()) == {"normalized_to_crc"}


def test_fx_producer_fails_when_missing_currency_rates(tmp_path, sample_income_csv):
    config = Config()
    with pytest.raises(ValueError, match="FX rates missing for currencies"):
        build_income_analysis_table_fx(
            repo_root=tmp_path,
            input_csv=sample_income_csv,
            config=config,
            fx_rates_to_crc={"CRC": 1.0},
            output_csv=ARTIFACTS.income_analysis_table_fx_csv,
        )


def test_fx_rates_source_of_truth_file_is_used_when_present(tmp_path):
    rates_path = tmp_path / "fx_rates.json"
    rates_path.write_text('{"USD": 510.0, "CRC": 1.0}', encoding="utf-8")

    rates = resolve_fx_rates_to_crc(
        fx_rates_json=None,
        fx_rates_file=str(rates_path),
        config_rates_to_crc=None,
    )
    assert rates == {"USD": 510.0, "CRC": 1.0}


def test_fx_rates_resolution_fails_without_any_source(tmp_path):
    with pytest.raises(ValueError):
        resolve_fx_rates_to_crc(
            fx_rates_json=None,
            fx_rates_file=str(tmp_path / "missing.json"),
            config_rates_to_crc=None,
        )

