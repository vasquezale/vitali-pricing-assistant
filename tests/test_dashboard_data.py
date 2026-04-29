from __future__ import annotations

from pathlib import Path

from vitali.dashboard.data import (
    DISPLAY_FX_CRC_PER_USD,
    build_income_history,
    format_currency_display,
    load_f7_monthly_balance,
    load_reservations,
    resolve_price_reference,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_income_history_reaches_january_2026() -> None:
    reservations = load_reservations(_repo_root())
    history = build_income_history(reservations, "CRC")
    assert history["month_label"].max() == "2026-01"


def test_usd_display_conversion_uses_fixed_visual_rate() -> None:
    value_crc = 46000
    formatted = format_currency_display(value_crc, "USD")
    assert str(DISPLAY_FX_CRC_PER_USD) == "460.0"
    assert "$100.0 USD" == formatted


def test_price_reference_fallback_is_hierarchical_for_missing_segment() -> None:
    reservations = load_reservations(_repo_root())
    reference = resolve_price_reference(reservations, unit_id="room_b", month=9, day_type="weekday")
    assert reference["fallback_level"] == "month"
    assert reference["fallback_label"] == "Referencia aproximada del mes"


def test_monthly_balance_dataset_still_loads_for_dashboard() -> None:
    balance = load_f7_monthly_balance(_repo_root())
    assert not balance.empty
    assert sorted(balance["year"].dropna().astype(int).unique().tolist()) == [2024, 2025, 2026]
