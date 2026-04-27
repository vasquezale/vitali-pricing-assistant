"""Loading and validation for anonymized income extracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd

from vitali.config import FxNormalizationConfig, IncomeDataConfig


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


def build_income_segment_summary(analysis_table: pd.DataFrame) -> dict[str, object]:
    """Aggregate the reservation-level analysis table without mixing currencies."""
    summary_scope = {
        "rows": int(len(analysis_table)),
        "currencies": sorted(analysis_table["currency"].dropna().unique().tolist()),
        "units": sorted(analysis_table["unit_id"].dropna().unique().tolist()),
        "fx_normalization_statuses": sorted(analysis_table["fx_normalization_status"].dropna().unique().tolist()),
        "check_in_min": _to_optional_date(analysis_table["check_in"].min()),
        "check_in_max": _to_optional_date(analysis_table["check_in"].max()),
    }

    by_unit_currency = _aggregate_income_segments(
        analysis_table,
        group_columns=["unit_id", "currency"],
    )
    by_month_currency = _aggregate_income_segments(
        analysis_table,
        group_columns=["check_in_year", "check_in_month", "currency"],
    )
    by_context_currency = _aggregate_income_segments(
        analysis_table,
        group_columns=["check_in_context", "currency"],
    )
    by_lead_bucket_currency = _aggregate_income_segments(
        analysis_table,
        group_columns=["lead_bucket", "currency"],
    )

    return {
        "summary_scope": summary_scope,
        "by_unit_currency": by_unit_currency,
        "by_month_currency": by_month_currency,
        "by_context_currency": by_context_currency,
        "by_lead_bucket_currency": by_lead_bucket_currency,
    }


def build_income_visual_summary(analysis_table: pd.DataFrame) -> dict[str, object]:
    """Aggregate reservation signals for lightweight time-series visualization."""
    summary_scope = {
        "rows": int(len(analysis_table)),
        "currencies": sorted(analysis_table["currency"].dropna().unique().tolist()),
        "units": sorted(analysis_table["unit_id"].dropna().unique().tolist()),
        "check_in_min": _to_optional_date(analysis_table["check_in"].min()),
        "check_in_max": _to_optional_date(analysis_table["check_in"].max()),
    }

    by_check_in_date = _aggregate_income_segments(
        analysis_table,
        group_columns=["check_in", "unit_id", "currency"],
    )
    by_month_unit_currency = _aggregate_income_segments(
        analysis_table,
        group_columns=["check_in_year", "check_in_month", "unit_id", "currency"],
    )
    by_month_context_currency = _aggregate_income_segments(
        analysis_table,
        group_columns=["check_in_month", "check_in_context", "currency"],
    )

    return {
        "summary_scope": summary_scope,
        "by_check_in_date": by_check_in_date,
        "by_month_unit_currency": by_month_unit_currency,
        "by_month_context_currency": by_month_context_currency,
    }


def build_income_segment_insights(summary: dict[str, object]) -> dict[str, object]:
    """Derive reproducible narrative insights from the segment summary."""
    insights: list[dict[str, object]] = []

    by_unit_currency = summary["by_unit_currency"]
    insights.extend(_build_unit_performance_insights(by_unit_currency))

    by_context_currency = summary["by_context_currency"]
    insights.extend(_build_weekend_weekday_insights(by_context_currency))

    by_lead_bucket_currency = summary["by_lead_bucket_currency"]
    insights.extend(_build_lead_bucket_insights(by_lead_bucket_currency))

    by_month_currency = summary["by_month_currency"]
    insights.extend(_build_month_peak_insights(by_month_currency))

    for insight in insights:
        confidence = _assess_insight_confidence(insight)
        insight["confidence_label"] = confidence["label"]
        insight["confidence_score"] = confidence["score"]
        insight["confidence_reason"] = confidence["reason"]

    primary_insights = [item for item in insights if item["confidence_label"] in {"high", "medium"}]
    appendix_insights = [item for item in insights if item["confidence_label"] == "low"]

    return {
        "summary_scope": summary["summary_scope"],
        "insight_count": len(insights),
        "primary_insight_count": len(primary_insights),
        "appendix_insight_count": len(appendix_insights),
        "insights": insights,
        "primary_insights": primary_insights,
        "appendix_insights": appendix_insights,
    }


def render_income_segment_insights_markdown(insights_payload: dict[str, object], source_name: str) -> str:
    """Render segment insights as a concise Markdown report."""
    scope = insights_payload["summary_scope"]
    lines = [
        "# Income Segment Insights",
        "",
        "These insights are derived mechanically from the segment summary and keep",
        "`currency` as a mandatory dimension for every monetary comparison.",
        "",
        "## Scope",
        f"- Source: `{source_name}`",
        f"- Rows analyzed: `{scope['rows']}`",
        f"- Currencies present: `{', '.join(scope['currencies'])}`",
        f"- Units present: `{', '.join(scope['units'])}`",
        f"- FX statuses present: `{', '.join(scope['fx_normalization_statuses'])}`",
        f"- Insight count: `{insights_payload['insight_count']}`",
        f"- Primary insight count: `{insights_payload['primary_insight_count']}`",
        f"- Appendix insight count: `{insights_payload['appendix_insight_count']}`",
        "",
        "## Primary Insights",
    ]
    for insight in insights_payload["primary_insights"]:
        lines.append(
            f"- [{insight['currency']}] ({insight['confidence_label']}) {insight['message']} "
            f"Support: {insight['confidence_reason']}."
        )

    if insights_payload["appendix_insights"]:
        lines.extend(["", "## Appendix: Low-Confidence Insights"])
        for insight in insights_payload["appendix_insights"]:
            lines.append(
                f"- [{insight['currency']}] ({insight['confidence_label']}) {insight['message']} "
                f"Support: {insight['confidence_reason']}."
            )
    lines.append("")
    return "\n".join(lines)


def render_income_segment_summary_markdown(summary: dict[str, object], source_name: str) -> str:
    """Render the segment summary in Markdown format."""
    scope = summary["summary_scope"]
    lines = [
        "# Income Segment Summary",
        "",
        "This report aggregates reservation-level income signals while keeping `currency`",
        "as a required grouping dimension for monetary metrics.",
        "",
        "## Scope",
        f"- Source: `{source_name}`",
        f"- Rows analyzed: `{scope['rows']}`",
        f"- Currencies present: `{', '.join(scope['currencies'])}`",
        f"- Units present: `{', '.join(scope['units'])}`",
        f"- FX statuses present: `{', '.join(scope['fx_normalization_statuses'])}`",
        f"- Check-in range: `{scope['check_in_min']}` to `{scope['check_in_max']}`",
        "",
    ]

    lines.extend(
        _render_segment_table(
            title="By Unit and Currency",
            rows=summary["by_unit_currency"],
            columns=[
                "unit_id",
                "currency",
                "reservations",
                "nights",
                "gross_income_sum",
                "net_amount_sum",
                "median_gross_adr",
                "median_net_adr",
            ],
        )
    )
    lines.extend(
        _render_segment_table(
            title="By Month and Currency",
            rows=summary["by_month_currency"],
            columns=[
                "check_in_year",
                "check_in_month",
                "currency",
                "reservations",
                "nights",
                "gross_income_sum",
                "net_amount_sum",
                "median_gross_adr",
            ],
        )
    )
    lines.extend(
        _render_segment_table(
            title="By Weekend/Weekday and Currency",
            rows=summary["by_context_currency"],
            columns=[
                "check_in_context",
                "currency",
                "reservations",
                "nights",
                "gross_income_sum",
                "net_amount_sum",
                "median_gross_adr",
            ],
        )
    )
    lines.extend(
        _render_segment_table(
            title="By Lead Bucket and Currency",
            rows=summary["by_lead_bucket_currency"],
            columns=[
                "lead_bucket",
                "currency",
                "reservations",
                "nights",
                "gross_income_sum",
                "net_amount_sum",
                "median_gross_adr",
            ],
        )
    )
    return "\n".join(lines) + "\n"


def resolve_fx_rates(config: FxNormalizationConfig) -> dict[str, float] | None:
    """Resolve the configured FX normalization policy into concrete rates or none.

    Supported strategies:
    - preserve_original: keep original currencies untouched.
    - manual_static: normalize using explicit user-declared currency-to-CRC rates.
    """
    if not config.enabled or config.strategy == "preserve_original":
        return None

    if config.strategy != "manual_static":
        raise ValueError(f"Unsupported FX normalization strategy: {config.strategy}")

    if config.target_currency != "CRC":
        raise ValueError("Current implementation only supports CRC as target currency.")

    rates = dict(config.rates_to_crc)
    if not rates:
        raise ValueError("FX normalization is enabled but no rates_to_crc were provided.")

    if "CRC" not in rates:
        rates["CRC"] = 1.0

    invalid_rates = [currency for currency, rate in rates.items() if rate <= 0]
    if invalid_rates:
        invalid = ", ".join(sorted(invalid_rates))
        raise ValueError(f"FX normalization rates must be positive for: {invalid}")

    return rates


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
    for row in sorted(
        summary["by_weekday_name"],
        key=lambda item: (item["currency"], weekday_order[item["check_in_weekday"]]),
    ):
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


def _aggregate_income_segments(
    frame: pd.DataFrame,
    group_columns: list[str],
) -> list[dict[str, object]]:
    grouped = frame.groupby(group_columns, dropna=False)
    rows: list[dict[str, object]] = []
    for keys, segment in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_columns, keys, strict=False))
        row.update(
            {
                "reservations": int(len(segment)),
                "nights": float(segment["nights"].sum()),
                "gross_income_sum": float(segment["gross_income"].sum()),
                "net_amount_sum": float(segment["net_amount"].sum()),
                "median_gross_adr": _to_optional_float(segment["gross_adr"].median()),
                "median_net_adr": _to_optional_float(segment["net_adr"].median()),
                "median_booking_lead_days": _to_optional_float(segment["booking_lead_days"].median()),
            }
        )
        rows.append(row)
    return rows


def _render_segment_table(title: str, rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    lines = [f"## {title}"]
    header = "| " + " | ".join(columns) + " |"
    divider = "|" + "|".join("---:" if _is_numeric_column(column) else "---" for column in columns) + "|"
    lines.extend([header, divider])
    for row in rows:
        rendered = []
        for column in columns:
            value = row.get(column)
            if isinstance(value, float):
                rendered.append(f"{value:.2f}")
            else:
                rendered.append(str(value))
        lines.append("| " + " | ".join(rendered) + " |")
    lines.append("")
    return lines


def _is_numeric_column(column: str) -> bool:
    return column in {
        "reservations",
        "nights",
        "gross_income_sum",
        "net_amount_sum",
        "median_gross_adr",
        "median_net_adr",
        "median_booking_lead_days",
        "check_in_year",
        "check_in_month",
    }


def _build_unit_performance_insights(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    insights: list[dict[str, object]] = []
    by_currency: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_currency.setdefault(row["currency"], []).append(row)

    for currency, currency_rows in by_currency.items():
        if len(currency_rows) < 2:
            continue
        ranked = sorted(currency_rows, key=lambda item: item["median_gross_adr"], reverse=True)
        top = ranked[0]
        bottom = ranked[-1]
        diff = top["median_gross_adr"] - bottom["median_gross_adr"]
        insights.append(
            {
                "kind": "unit_adr_gap",
                "currency": currency,
                "message": (
                    f"{top['unit_id']} shows the highest median gross ADR at {top['median_gross_adr']:.2f}, "
                    f"above {bottom['unit_id']} by {diff:.2f}."
                ),
                "evidence": {
                    "top_unit": top["unit_id"],
                    "top_median_gross_adr": top["median_gross_adr"],
                    "bottom_unit": bottom["unit_id"],
                    "bottom_median_gross_adr": bottom["median_gross_adr"],
                    "top_reservations": top["reservations"],
                    "bottom_reservations": bottom["reservations"],
                },
            }
        )
    return insights


def _build_weekend_weekday_insights(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    insights: list[dict[str, object]] = []
    by_currency_context = {(row["currency"], row["check_in_context"]): row for row in rows}
    currencies = sorted({row["currency"] for row in rows})
    for currency in currencies:
        weekday = by_currency_context.get((currency, "weekday"))
        weekend = by_currency_context.get((currency, "weekend"))
        if not weekday or not weekend:
            continue
        diff = weekend["median_gross_adr"] - weekday["median_gross_adr"]
        direction = "higher" if diff >= 0 else "lower"
        insights.append(
            {
                "kind": "weekend_weekday_gap",
                "currency": currency,
                "message": (
                    f"Weekend check-ins show {direction} median gross ADR than weekday check-ins by "
                    f"{abs(diff):.2f}."
                ),
                "evidence": {
                    "weekend_median_gross_adr": weekend["median_gross_adr"],
                    "weekday_median_gross_adr": weekday["median_gross_adr"],
                    "weekend_reservations": weekend["reservations"],
                    "weekday_reservations": weekday["reservations"],
                },
            }
        )
    return insights


def _build_lead_bucket_insights(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    insights: list[dict[str, object]] = []
    by_currency: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_currency.setdefault(row["currency"], []).append(row)

    order = {"0-3": 0, "4-7": 1, "8-14": 2, "15-30": 3, "31+": 4, "unknown": 5}
    for currency, currency_rows in by_currency.items():
        ranked = sorted(currency_rows, key=lambda item: item["median_gross_adr"], reverse=True)
        top = ranked[0]
        earliest = min(currency_rows, key=lambda item: order.get(item["lead_bucket"], 99))
        if top["lead_bucket"] == earliest["lead_bucket"]:
            continue
        insights.append(
            {
                "kind": "lead_bucket_peak",
                "currency": currency,
                "message": (
                    f"The highest median gross ADR appears in lead bucket {top['lead_bucket']} at "
                    f"{top['median_gross_adr']:.2f}, versus {earliest['lead_bucket']} at "
                    f"{earliest['median_gross_adr']:.2f}."
                ),
                "evidence": {
                    "top_lead_bucket": top["lead_bucket"],
                    "top_median_gross_adr": top["median_gross_adr"],
                    "top_reservations": top["reservations"],
                    "earliest_lead_bucket": earliest["lead_bucket"],
                    "earliest_median_gross_adr": earliest["median_gross_adr"],
                    "earliest_reservations": earliest["reservations"],
                },
            }
        )
    return insights


def _build_month_peak_insights(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    insights: list[dict[str, object]] = []
    by_currency: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_currency.setdefault(row["currency"], []).append(row)

    for currency, currency_rows in by_currency.items():
        top = max(currency_rows, key=lambda item: item["median_gross_adr"])
        insights.append(
            {
                "kind": "monthly_peak",
                "currency": currency,
                "message": (
                    f"The monthly peak median gross ADR appears in {int(top['check_in_year'])}-"
                    f"{int(top['check_in_month']):02d} at {top['median_gross_adr']:.2f}."
                ),
                "evidence": {
                    "check_in_year": top["check_in_year"],
                    "check_in_month": top["check_in_month"],
                    "median_gross_adr": top["median_gross_adr"],
                    "reservations": top["reservations"],
                },
            }
        )
    return insights


def _assess_insight_confidence(insight: dict[str, object]) -> dict[str, object]:
    evidence = insight["evidence"]
    kind = insight["kind"]

    if kind == "unit_adr_gap":
        support = min(evidence["top_reservations"], evidence["bottom_reservations"])
        return _confidence_from_support(
            support,
            reason=f"minimum segment support is {support} reservations across the compared units",
        )

    if kind == "weekend_weekday_gap":
        support = min(evidence["weekend_reservations"], evidence["weekday_reservations"])
        return _confidence_from_support(
            support,
            reason=f"minimum context support is {support} reservations across weekend vs weekday",
        )

    if kind == "lead_bucket_peak":
        support = min(evidence["top_reservations"], evidence["earliest_reservations"])
        return _confidence_from_support(
            support,
            reason=f"minimum bucket support is {support} reservations across the compared lead buckets",
        )

    if kind == "monthly_peak":
        support = evidence["reservations"]
        return _confidence_from_support(
            support,
            reason=f"peak month segment contains {support} reservations",
        )

    return {"label": "unknown", "score": 0.0, "reason": "no confidence rule defined"}


def _confidence_from_support(support: int, reason: str) -> dict[str, object]:
    if support >= 30:
        return {"label": "high", "score": 0.9, "reason": reason}
    if support >= 12:
        return {"label": "medium", "score": 0.6, "reason": reason}
    return {"label": "low", "score": 0.3, "reason": reason}
