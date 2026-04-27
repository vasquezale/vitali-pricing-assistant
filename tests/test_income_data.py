"""Tests for anonymized income data loading and profiling."""

from pathlib import Path

import pandas as pd
import pytest

from vitali.config import FxNormalizationConfig, IncomeDataConfig
from vitali.data.income import (
    build_income_analysis_table,
    build_income_segment_insights,
    build_income_profile,
    build_income_segment_summary,
    build_income_summary,
    load_income_data,
    render_income_segment_insights_markdown,
    render_income_segment_summary_markdown,
    render_income_summary_markdown,
    resolve_fx_rates,
)


@pytest.fixture()
def sample_income_csv(tmp_path: Path) -> Path:
    """Create a small anonymized income extract for tests."""
    frame = pd.DataFrame(
        {
            "record_type": ["reservation", "reservation", "resolution_payment"],
            "movement_date": ["2026-01-05", "2026-01-06", "2026-01-06"],
            "booking_date": ["2025-12-20", "2025-12-22", "2025-12-23"],
            "check_in": ["2026-01-10", "2026-01-12", "2026-01-12"],
            "check_out": ["2026-01-11", "2026-01-14", "2026-01-13"],
            "nights": [1, 2, 1],
            "unit_id": ["room_a", "room_b", "room_b"],
            "currency": ["USD", "CRC", "USD"],
            "net_amount": [120.0, 180000.0, 40.0],
            "service_fee": [4.0, 6000.0, 0.0],
            "quick_pay_fee": [None, None, None],
            "cleaning_fee": [20.0, 0.0, None],
            "gross_income": [124.0, 186000.0, 40.0],
            "lodging_tax": [0.0, 0.0, 0.0],
            "income_year": [2026, 2026, 2026],
            "booking_lead_days": [21, 21, 20],
        }
    )
    path = tmp_path / "income.csv"
    frame.to_csv(path, index=False)
    return path


def test_load_income_data_parses_dates_and_numbers(sample_income_csv: Path) -> None:
    dataset = load_income_data(sample_income_csv, IncomeDataConfig())

    assert str(dataset.source_path) == str(sample_income_csv)
    assert pd.api.types.is_datetime64_any_dtype(dataset.records["check_in"])
    assert pd.api.types.is_numeric_dtype(dataset.records["gross_income"])


def test_load_income_data_rejects_unknown_currency(sample_income_csv: Path) -> None:
    bad_frame = pd.read_csv(sample_income_csv)
    bad_frame.loc[0, "currency"] = "EUR"
    bad_path = sample_income_csv.parent / "bad_income.csv"
    bad_frame.to_csv(bad_path, index=False)

    with pytest.raises(ValueError, match="Unsupported currencies"):
        load_income_data(bad_path, IncomeDataConfig())


def test_build_income_profile_returns_currency_segmented_metrics(sample_income_csv: Path) -> None:
    dataset = load_income_data(sample_income_csv, IncomeDataConfig())
    profile = build_income_profile(dataset.records)

    assert profile["source_rows"] == 3
    assert profile["reservation_rows"] == 2
    assert profile["resolution_payment_rows"] == 1
    assert profile["currencies"] == ["CRC", "USD"]
    assert profile["units"] == ["room_a", "room_b"]
    assert profile["date_range"] == {
        "check_in_min": "2026-01-10",
        "check_in_max": "2026-01-12",
    }
    assert profile["stay_length_distribution"] == {"1": 1, "2": 1}


def test_build_income_summary_segments_weekend_and_lead_time(sample_income_csv: Path) -> None:
    dataset = load_income_data(sample_income_csv, IncomeDataConfig())
    summary = build_income_summary(dataset.records)

    assert summary["summary_scope"]["reservation_rows"] == 2
    assert summary["summary_scope"]["currencies"] == ["CRC", "USD"]
    assert summary["summary_scope"]["units"] == ["room_a", "room_b"]
    assert any(row["check_in_context"] == "weekday" for row in summary["by_check_in_context"])
    assert any(row["lead_bucket"] == "15-30" for row in summary["by_lead_bucket"])


def test_render_income_summary_markdown_contains_key_sections(sample_income_csv: Path) -> None:
    dataset = load_income_data(sample_income_csv, IncomeDataConfig())
    summary = build_income_summary(dataset.records)

    report = render_income_summary_markdown(summary, str(dataset.source_path))

    assert "# Income Summary" in report
    assert "## By Unit and Currency" in report
    assert "## Weekend vs Weekday Check-in" in report
    assert "## Booking Lead Buckets" in report


def test_build_income_analysis_table_preserves_original_currency_when_no_fx(sample_income_csv: Path) -> None:
    dataset = load_income_data(sample_income_csv, IncomeDataConfig())

    table = build_income_analysis_table(dataset.records)

    assert len(table) == 2
    assert set(table["fx_normalization_status"]) == {"original_currency_only"}
    assert table["gross_income_crc"].isna().all()
    assert set(table["check_in_context"]) == {"weekday", "weekend"}


def test_build_income_analysis_table_normalizes_when_fx_rates_are_provided(sample_income_csv: Path) -> None:
    dataset = load_income_data(sample_income_csv, IncomeDataConfig())

    table = build_income_analysis_table(dataset.records, fx_rates_to_crc={"USD": 510.0, "CRC": 1.0})

    usd_row = table.loc[table["currency"] == "USD"].iloc[0]
    crc_row = table.loc[table["currency"] == "CRC"].iloc[0]

    assert usd_row["fx_normalization_status"] == "normalized_to_crc"
    assert crc_row["fx_normalization_status"] == "normalized_to_crc"
    assert usd_row["gross_income_crc"] == pytest.approx(124.0 * 510.0)
    assert crc_row["gross_income_crc"] == pytest.approx(186000.0)


def test_resolve_fx_rates_returns_none_for_preserve_original() -> None:
    policy = FxNormalizationConfig(enabled=False, strategy="preserve_original")

    assert resolve_fx_rates(policy) is None


def test_resolve_fx_rates_builds_manual_static_policy() -> None:
    policy = FxNormalizationConfig(
        enabled=True,
        strategy="manual_static",
        target_currency="CRC",
        rates_to_crc={"USD": 510.0},
    )

    rates = resolve_fx_rates(policy)

    assert rates == {"USD": 510.0, "CRC": 1.0}


def test_resolve_fx_rates_rejects_missing_manual_rates() -> None:
    policy = FxNormalizationConfig(enabled=True, strategy="manual_static", target_currency="CRC")

    with pytest.raises(ValueError, match="no rates_to_crc"):
        resolve_fx_rates(policy)


def test_build_income_segment_summary_keeps_currency_as_grouping_axis(sample_income_csv: Path) -> None:
    dataset = load_income_data(sample_income_csv, IncomeDataConfig())
    table = build_income_analysis_table(dataset.records)

    summary = build_income_segment_summary(table)

    assert summary["summary_scope"]["currencies"] == ["CRC", "USD"]
    assert summary["summary_scope"]["fx_normalization_statuses"] == ["original_currency_only"]
    assert all("currency" in row for row in summary["by_unit_currency"])
    assert all("currency" in row for row in summary["by_month_currency"])
    assert all("currency" in row for row in summary["by_context_currency"])
    assert all("currency" in row for row in summary["by_lead_bucket_currency"])


def test_render_income_segment_summary_markdown_contains_safe_sections(sample_income_csv: Path) -> None:
    dataset = load_income_data(sample_income_csv, IncomeDataConfig())
    table = build_income_analysis_table(dataset.records)
    summary = build_income_segment_summary(table)

    report = render_income_segment_summary_markdown(summary, dataset.source_path.name)

    assert "# Income Segment Summary" in report
    assert "## By Unit and Currency" in report
    assert "## By Month and Currency" in report
    assert "## By Weekend/Weekday and Currency" in report
    assert "## By Lead Bucket and Currency" in report


def test_build_income_segment_insights_returns_currency_scoped_findings(sample_income_csv: Path) -> None:
    dataset = load_income_data(sample_income_csv, IncomeDataConfig())
    table = build_income_analysis_table(dataset.records)
    summary = build_income_segment_summary(table)

    insights = build_income_segment_insights(summary)

    assert insights["summary_scope"]["currencies"] == ["CRC", "USD"]
    assert insights["insight_count"] >= 2
    assert all("currency" in item for item in insights["insights"])
    assert all("message" in item for item in insights["insights"])


def test_render_income_segment_insights_markdown_contains_insight_section(sample_income_csv: Path) -> None:
    dataset = load_income_data(sample_income_csv, IncomeDataConfig())
    table = build_income_analysis_table(dataset.records)
    summary = build_income_segment_summary(table)
    insights = build_income_segment_insights(summary)

    report = render_income_segment_insights_markdown(insights, dataset.source_path.name)

    assert "# Income Segment Insights" in report
    assert "## Insights" in report
    assert "- [CRC]" in report or "- [USD]" in report
