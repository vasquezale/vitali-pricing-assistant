"""Light-weight validation for Phase 2 monthly reconciliation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class DataQualityReport:
    """Result of `validate_pipeline_inputs`."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)


def validate_pipeline_inputs(
    expenses: pd.DataFrame,
    income: pd.DataFrame,
    *,
    low_booking_threshold: int = 5,
) -> DataQualityReport:
    """Validate merged expense + income frames before reconciliation."""
    errors: list[str] = []
    alerts: list[str] = []

    required_exp = ["fecha", "monto_crc"]
    for col in required_exp:
        if col not in expenses.columns:
            errors.append(f"Expenses missing column: {col}")

    required_inc = ["check_in", "gross_income_crc"]
    for col in required_inc:
        if col not in income.columns:
            errors.append(f"Income missing column: {col}")

    if errors:
        return DataQualityReport(is_valid=False, errors=errors, alerts=alerts)

    if expenses["monto_crc"].isna().all():
        errors.append("All expense amounts are null")

    neg_exp = (expenses["monto_crc"] < 0).sum()
    if neg_exp > 0:
        alerts.append(f"Expense rows with negative monto_crc: {int(neg_exp)}")

    null_dates = expenses["fecha"].isna().sum()
    if null_dates > 0:
        alerts.append(f"Expense rows with null fecha: {int(null_dates)}")

    null_inc = income["check_in"].isna().sum()
    if null_inc > 0:
        alerts.append(f"Income rows with null check_in: {int(null_inc)}")

    if "check_in_year" in income.columns and "check_in_month" in income.columns:
        g = income.dropna(subset=["check_in"]).groupby(["check_in_year", "check_in_month"], sort=True)
        counts = g.size()
        sparse = counts[counts < low_booking_threshold]
        for (y, m), n in sparse.items():
            alerts.append(f"Low booking count for {int(y)}-{int(m):02d}: {int(n)} (< {low_booking_threshold})")

    return DataQualityReport(is_valid=len(errors) == 0, errors=errors, alerts=alerts)
