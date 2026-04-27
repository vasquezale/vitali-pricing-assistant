"""Loading and validation for anonymized income extracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd

from vitali.config import IncomeDataConfig


@dataclass
class IncomeDataset:
    """In-memory representation of the anonymized income extract."""

    records: pd.DataFrame
    source_path: Path


def load_income_data(source_path: str | Path, config: IncomeDataConfig) -> IncomeDataset:
    """Load the anonymized income extract with basic type normalization."""
    path = Path(source_path)
    records = pd.read_csv(path)

    missing_columns = sorted(set(config.required_columns) - set(records.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Income extract is missing required columns: {missing}")

    for column in config.date_columns:
        records[column] = pd.to_datetime(records[column], errors="coerce")

    numeric_columns = [
        "nights",
        "net_amount",
        "service_fee",
        "quick_pay_fee",
        "cleaning_fee",
        "gross_income",
        "lodging_tax",
        "income_year",
        "booking_lead_days",
    ]
    for column in numeric_columns:
        if column in records.columns:
            records[column] = pd.to_numeric(records[column], errors="coerce")

    validate_income_data(records, config)
    return IncomeDataset(records=records, source_path=path)


def validate_income_data(records: pd.DataFrame, config: IncomeDataConfig) -> None:
    """Validate the most important invariants of the anonymized extract."""
    invalid_record_types = sorted(set(records["record_type"].dropna()) - set(config.allowed_record_types))
    if invalid_record_types:
        raise ValueError(f"Unsupported record types found: {', '.join(invalid_record_types)}")

    invalid_currencies = sorted(set(records["currency"].dropna()) - set(config.allowed_currencies))
    if invalid_currencies:
        raise ValueError(f"Unsupported currencies found: {', '.join(invalid_currencies)}")

    reservation_rows = records["record_type"] == "reservation"
    if reservation_rows.any():
        missing_check_in = records.loc[reservation_rows, "check_in"].isna().any()
        missing_check_out = records.loc[reservation_rows, "check_out"].isna().any()
        missing_nights = records.loc[reservation_rows, "nights"].isna().any()
        if missing_check_in or missing_check_out or missing_nights:
            raise ValueError("Reservation rows must have check-in, check-out, and nights.")

        non_positive_nights = (records.loc[reservation_rows, "nights"] <= 0).any()
        if non_positive_nights:
            raise ValueError("Reservation rows must have positive nights.")


def build_income_profile(records: pd.DataFrame) -> dict[str, object]:
    """Produce a compact profile for reproducible income analysis."""
    reservation_rows = records["record_type"] == "reservation"
    reservations = records.loc[reservation_rows].copy()
    reservations["gross_adr"] = reservations["gross_income"] / reservations["nights"]
    reservations["net_adr"] = reservations["net_amount"] / reservations["nights"]

    reservations_by_currency = []
    for currency, frame in reservations.groupby("currency", dropna=False):
        reservations_by_currency.append(
            {
                "currency": currency,
                "reservations": int(len(frame)),
                "nights": float(frame["nights"].sum()),
                "median_booking_lead_days": _to_optional_float(frame["booking_lead_days"].median()),
            }
        )

    unit_currency_metrics = []
    grouped = reservations.groupby(["unit_id", "currency"], dropna=False)
    for (unit_id, currency), frame in grouped:
        unit_currency_metrics.append(
            {
                "unit_id": unit_id,
                "currency": currency,
                "reservations": int(len(frame)),
                "nights": float(frame["nights"].sum()),
                "median_gross_adr": _to_optional_float(frame["gross_adr"].median()),
                "median_net_adr": _to_optional_float(frame["net_adr"].median()),
                "median_booking_lead_days": _to_optional_float(frame["booking_lead_days"].median()),
            }
        )

    stay_length_distribution = {
        str(int(length)): int(count)
        for length, count in reservations["nights"].value_counts().sort_index().items()
    }

    return {
        "source_rows": int(len(records)),
        "reservation_rows": int(reservation_rows.sum()),
        "resolution_payment_rows": int((records["record_type"] == "resolution_payment").sum()),
        "currencies": sorted(records["currency"].dropna().unique().tolist()),
        "units": sorted(records["unit_id"].dropna().unique().tolist()),
        "date_range": {
            "check_in_min": _to_optional_date(reservations["check_in"].min()),
            "check_in_max": _to_optional_date(reservations["check_in"].max()),
        },
        "reservations_by_currency": reservations_by_currency,
        "unit_currency_metrics": unit_currency_metrics,
        "stay_length_distribution": stay_length_distribution,
    }


def build_income_summary(records: pd.DataFrame) -> dict[str, object]:
    """Produce an analytical summary segmented by room, currency, lead time, and weekend."""
    reservation_rows = records["record_type"] == "reservation"
    reservations = records.loc[reservation_rows].copy()
    reservations["gross_adr"] = reservations["gross_income"] / reservations["nights"]
    reservations["net_adr"] = reservations["net_amount"] / reservations["nights"]
    reservations["check_in_weekday"] = reservations["check_in"].dt.day_name()
    reservations["check_in_dayofweek"] = reservations["check_in"].dt.dayofweek
    reservations["check_in_context"] = reservations["check_in_dayofweek"].map(
        lambda day: "weekend" if day >= 4 else "weekday"
    )
    reservations["lead_bucket"] = reservations["booking_lead_days"].map(_bucket_lead_days)

    by_unit_currency = []
    for (unit_id, currency), frame in reservations.groupby(["unit_id", "currency"], dropna=False):
        by_unit_currency.append(
            {
                "unit_id": unit_id,
                "currency": currency,
                "reservations": int(len(frame)),
                "nights": float(frame["nights"].sum()),
                "median_gross_adr": _to_optional_float(frame["gross_adr"].median()),
                "median_net_adr": _to_optional_float(frame["net_adr"].median()),
                "median_booking_lead_days": _to_optional_float(frame["booking_lead_days"].median()),
            }
        )

    by_check_in_context = []
    for (currency, context), frame in reservations.groupby(["currency", "check_in_context"], dropna=False):
        by_check_in_context.append(
            {
                "currency": currency,
                "check_in_context": context,
                "reservations": int(len(frame)),
                "nights": float(frame["nights"].sum()),
                "median_gross_adr": _to_optional_float(frame["gross_adr"].median()),
                "median_net_adr": _to_optional_float(frame["net_adr"].median()),
            }
        )

    by_lead_bucket = []
    for (currency, lead_bucket), frame in reservations.groupby(["currency", "lead_bucket"], dropna=False):
        by_lead_bucket.append(
            {
                "currency": currency,
                "lead_bucket": lead_bucket,
                "reservations": int(len(frame)),
                "nights": float(frame["nights"].sum()),
                "median_gross_adr": _to_optional_float(frame["gross_adr"].median()),
                "median_net_adr": _to_optional_float(frame["net_adr"].median()),
            }
        )

    by_weekday_name = []
    for (currency, weekday_name), frame in reservations.groupby(["currency", "check_in_weekday"], dropna=False):
        by_weekday_name.append(
            {
                "currency": currency,
                "check_in_weekday": weekday_name,
                "reservations": int(len(frame)),
                "median_gross_adr": _to_optional_float(frame["gross_adr"].median()),
            }
        )

    return {
        "summary_scope": {
            "reservation_rows": int(len(reservations)),
            "currencies": sorted(reservations["currency"].dropna().unique().tolist()),
            "units": sorted(reservations["unit_id"].dropna().unique().tolist()),
            "check_in_min": _to_optional_date(reservations["check_in"].min()),
            "check_in_max": _to_optional_date(reservations["check_in"].max()),
        },
        "by_unit_currency": by_unit_currency,
        "by_check_in_context": by_check_in_context,
        "by_lead_bucket": by_lead_bucket,
        "by_weekday_name": by_weekday_name,
    }


def build_income_analysis_table(
    records: pd.DataFrame,
    fx_rates_to_crc: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Create a reproducible reservation-level table for downstream analysis.

    If exchange rates are not provided, monetary values are preserved in original
    currency and normalization fields stay null. This avoids silent cross-currency
    aggregation.
    """
    reservation_rows = records["record_type"] == "reservation"
    reservations = records.loc[reservation_rows].copy()

    reservations["gross_adr"] = reservations["gross_income"] / reservations["nights"]
    reservations["net_adr"] = reservations["net_amount"] / reservations["nights"]
    reservations["service_fee_rate"] = reservations["service_fee"] / reservations["gross_income"]
    reservations["cleaning_fee_per_night"] = reservations["cleaning_fee"] / reservations["nights"]
    reservations["check_in_year"] = reservations["check_in"].dt.year
    reservations["check_in_month"] = reservations["check_in"].dt.month
    reservations["check_in_week"] = reservations["check_in"].dt.isocalendar().week.astype("Int64")
    reservations["check_in_dayofweek"] = reservations["check_in"].dt.dayofweek
    reservations["check_in_weekday"] = reservations["check_in"].dt.day_name()
    reservations["check_in_context"] = reservations["check_in_dayofweek"].map(
        lambda day: "weekend" if day >= 4 else "weekday"
    )
    reservations["lead_bucket"] = reservations["booking_lead_days"].map(_bucket_lead_days)

    reservations["fx_rate_to_crc"] = reservations["currency"].map(dict(fx_rates_to_crc or {}))
    reservations["gross_income_crc"] = reservations["gross_income"] * reservations["fx_rate_to_crc"]
    reservations["net_amount_crc"] = reservations["net_amount"] * reservations["fx_rate_to_crc"]
    reservations["gross_adr_crc"] = reservations["gross_adr"] * reservations["fx_rate_to_crc"]
    reservations["net_adr_crc"] = reservations["net_adr"] * reservations["fx_rate_to_crc"]
    reservations["fx_normalization_status"] = reservations["fx_rate_to_crc"].map(
        lambda rate: "normalized_to_crc" if pd.notna(rate) else "original_currency_only"
    )

    selected_columns = [
        "unit_id",
        "currency",
        "check_in",
        "check_out",
        "booking_date",
        "movement_date",
        "income_year",
        "check_in_year",
        "check_in_month",
        "check_in_week",
        "check_in_dayofweek",
        "check_in_weekday",
        "check_in_context",
        "nights",
        "booking_lead_days",
        "lead_bucket",
        "gross_income",
        "net_amount",
        "gross_adr",
        "net_adr",
        "service_fee",
        "service_fee_rate",
        "cleaning_fee",
        "cleaning_fee_per_night",
        "lodging_tax",
        "fx_rate_to_crc",
        "gross_income_crc",
        "net_amount_crc",
        "gross_adr_crc",
        "net_adr_crc",
        "fx_normalization_status",
    ]
    return reservations[selected_columns].sort_values(["check_in", "unit_id"]).reset_index(drop=True)


def render_income_summary_markdown(summary: dict[str, object], source_name: str) -> str:
    """Render the analytical summary as a compact Markdown report."""
    scope = summary["summary_scope"]
    lines = [
        "# Income Summary",
        "",
        "This report is a reproducible descriptive summary of the anonymized income extract.",
        "It is useful for technical preparation and business orientation, but it is not a substitute",
        "for Fase 1 closeout, profitability analysis, or a full Fase 2 viability gate.",
        "",
        "## Scope",
        f"- Source: `{source_name}`",
        f"- Reservation rows analyzed: `{scope['reservation_rows']}`",
        f"- Currencies present: `{', '.join(scope['currencies'])}`",
        f"- Units present: `{', '.join(scope['units'])}`",
        f"- Check-in range: `{scope['check_in_min']}` to `{scope['check_in_max']}`",
        "",
        "## By Unit and Currency",
        "| unit_id | currency | reservations | nights | median_gross_adr | median_net_adr | median_booking_lead_days |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary["by_unit_currency"]:
        lines.append(
            "| {unit_id} | {currency} | {reservations} | {nights:.0f} | {median_gross_adr:.2f} | "
            "{median_net_adr:.2f} | {median_booking_lead_days:.1f} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Weekend vs Weekday Check-in",
            "| currency | check_in_context | reservations | nights | median_gross_adr | median_net_adr |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary["by_check_in_context"]:
        lines.append(
            "| {currency} | {check_in_context} | {reservations} | {nights:.0f} | {median_gross_adr:.2f} | "
            "{median_net_adr:.2f} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Booking Lead Buckets",
            "| currency | lead_bucket | reservations | nights | median_gross_adr | median_net_adr |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary["by_lead_bucket"]:
        lines.append(
            "| {currency} | {lead_bucket} | {reservations} | {nights:.0f} | {median_gross_adr:.2f} | "
            "{median_net_adr:.2f} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Check-in Weekday Detail",
            "| currency | check_in_weekday | reservations | median_gross_adr |",
            "|---|---|---:|---:|",
        ]
    )
    weekday_order = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }
    for row in sorted(summary["by_weekday_name"], key=lambda item: (item["currency"], weekday_order[item["check_in_weekday"]])):
        lines.append(
            "| {currency} | {check_in_weekday} | {reservations} | {median_gross_adr:.2f} |".format(**row)
        )

    return "\n".join(lines) + "\n"


def _to_optional_date(value: pd.Timestamp) -> str | None:
    if pd.isna(value):
        return None
    return value.date().isoformat()


def _to_optional_float(value: float) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _bucket_lead_days(value: float) -> str:
    if pd.isna(value):
        return "unknown"
    if value <= 3:
        return "0-3"
    if value <= 7:
        return "4-7"
    if value <= 14:
        return "8-14"
    if value <= 30:
        return "15-30"
    return "31+"
