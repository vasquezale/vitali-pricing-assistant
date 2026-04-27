"""Generate lightweight visual diagnostics for room income behavior over time."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from vitali.config import Config
from vitali.data.income import (
    build_income_analysis_table,
    build_income_visual_summary,
    load_income_data,
    resolve_fx_rates,
)

UNIT_LABELS = {
    "room_a": "CieloRosa",
    "room_b": "Aqua",
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml", help="Path to project YAML configuration.")
    parser.add_argument("--input", default=None, help="Optional override for the anonymized income CSV path.")
    parser.add_argument(
        "--output-dir",
        default="artifacts/income_trends",
        help="Directory where the charts and supporting files will be written.",
    )
    parser.add_argument(
        "--fx-rates-json",
        default=None,
        help="Optional JSON object with currency-to-CRC rates, e.g. '{\"USD\":510.0,\"CRC\":1.0}'. Overrides config.",
    )
    return parser.parse_args()


def _frame_from_rows(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    if "unit_id" in frame.columns:
        frame["unit_label"] = frame["unit_id"].map(UNIT_LABELS).fillna(frame["unit_id"])
    if "check_in" in frame.columns:
        frame["check_in"] = pd.to_datetime(frame["check_in"])
    if {"check_in_year", "check_in_month"}.issubset(frame.columns):
        frame["month_start"] = pd.to_datetime(
            {
                "year": frame["check_in_year"],
                "month": frame["check_in_month"],
                "day": 1,
            }
        )
        frame["month_label"] = frame["month_start"].dt.strftime("%Y-%m")
    return frame


def _render_chart(
    frame: pd.DataFrame,
    x_column: str,
    y_column: str,
    title: str,
    y_label: str,
    output_path: Path,
) -> None:
    currencies = sorted(frame["currency"].dropna().unique().tolist())
    fig, axes = plt.subplots(len(currencies), 1, figsize=(12, 4 * max(len(currencies), 1)), sharex=True)
    if len(currencies) == 1:
        axes = [axes]

    palette = {"CieloRosa": "#d6725b", "Aqua": "#2b8c7e"}

    for axis, currency in zip(axes, currencies, strict=True):
        currency_frame = frame.loc[frame["currency"] == currency].copy()
        sns.lineplot(
            data=currency_frame,
            x=x_column,
            y=y_column,
            hue="unit_label",
            marker="o",
            linewidth=2.2,
            palette=palette,
            ax=axis,
        )
        axis.set_title(f"{title} — {currency}")
        axis.set_ylabel(y_label)
        axis.set_xlabel("")
        axis.grid(True, alpha=0.25)
        axis.legend(title="Habitacion")
        axis.tick_params(axis="x", rotation=45)

    axes[-1].set_xlabel("Periodo")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _render_context_chart(frame: pd.DataFrame, output_path: Path) -> None:
    frame = frame.copy()
    frame["month_label"] = frame["check_in_month"].map(lambda month: f"{int(month):02d}")
    currencies = sorted(frame["currency"].dropna().unique().tolist())
    fig, axes = plt.subplots(1, len(currencies), figsize=(7 * max(len(currencies), 1), 5), sharey=False)
    if len(currencies) == 1:
        axes = [axes]

    for axis, currency in zip(axes, currencies, strict=True):
        currency_frame = frame.loc[frame["currency"] == currency].copy()
        sns.barplot(
            data=currency_frame,
            x="month_label",
            y="median_gross_adr",
            hue="check_in_context",
            palette={"weekday": "#7aa6c2", "weekend": "#f28e5b"},
            ax=axis,
        )
        axis.set_title(f"Median ADR by Month and Check-in Context — {currency}")
        axis.set_xlabel("Month")
        axis.set_ylabel("Median gross ADR")
        axis.tick_params(axis="x", rotation=45)
        axis.grid(True, alpha=0.2, axis="y")
        axis.legend(title="context")

    fig.tight_layout()
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _render_markdown_report(
    source_name: str,
    summary: dict[str, object],
    monthly_frame: pd.DataFrame,
) -> str:
    scope = summary["summary_scope"]
    unit_labels = [UNIT_LABELS.get(unit_id, unit_id) for unit_id in scope["units"]]
    lines = [
        "# Income Trend Visual Summary",
        "",
        f"- Source: `{source_name}`",
        f"- Rows analyzed: `{scope['rows']}`",
        f"- Currencies present: `{', '.join(scope['currencies'])}`",
        f"- Units present: `{', '.join(unit_labels)}`",
        f"- Check-in range: `{scope['check_in_min']}` to `{scope['check_in_max']}`",
        "",
        "## Quick Reading Guide",
        "- `monthly_reservations_by_room.png`: how bookings evolve over time by room.",
        "- `monthly_gross_income_by_room.png`: how gross income moves over time by room.",
        "- `monthly_median_adr_by_room.png`: how typical nightly rate changes by room.",
        "- `monthly_context_adr.png`: whether weekend check-ins tend to outperform weekdays by month.",
        "",
        "## Highest Monthly Peaks by Currency and Room",
    ]

    for currency in sorted(monthly_frame["currency"].dropna().unique().tolist()):
        currency_frame = monthly_frame.loc[monthly_frame["currency"] == currency]
        for unit_id in sorted(currency_frame["unit_id"].dropna().unique().tolist()):
            unit_frame = currency_frame.loc[currency_frame["unit_id"] == unit_id]
            if unit_frame.empty:
                continue
            unit_label = UNIT_LABELS.get(unit_id, unit_id)
            top_res = unit_frame.sort_values("reservations", ascending=False).iloc[0]
            top_income = unit_frame.sort_values("gross_income_sum", ascending=False).iloc[0]
            top_adr = unit_frame.sort_values("median_gross_adr", ascending=False).iloc[0]
            lines.append(
                f"- `{currency}` / `{unit_label}`: max reservations in `{top_res['month_label']}` "
                f"({int(top_res['reservations'])}), max gross income in `{top_income['month_label']}` "
                f"({top_income['gross_income_sum']:.2f}), max median ADR in `{top_adr['month_label']}` "
                f"({top_adr['median_gross_adr']:.2f})."
            )

    lines.extend(
        [
            "",
            "## Caveats",
            "- The charts keep `currency` separated on purpose; do not compare `USD` and `CRC` values directly.",
            "- These visuals describe observed income behavior, not causal effects.",
            "- Months with few reservations can show sharp jumps in ADR.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    """Load the anonymized income extract and generate time-based charts."""
    args = parse_args()
    config = Config.from_yaml(args.config)
    input_path = args.input or config.income_data.source_file
    dataset = load_income_data(input_path, config.income_data)
    fx_rates = json.loads(args.fx_rates_json) if args.fx_rates_json else resolve_fx_rates(config.fx_normalization)

    sns.set_theme(style="whitegrid")

    analysis_table = build_income_analysis_table(dataset.records, fx_rates_to_crc=fx_rates)
    visual_summary = build_income_visual_summary(analysis_table)

    date_frame = _frame_from_rows(visual_summary["by_check_in_date"])
    monthly_frame = _frame_from_rows(visual_summary["by_month_unit_currency"])
    context_frame = _frame_from_rows(visual_summary["by_month_context_currency"])

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    monthly_frame.to_csv(output_dir / "monthly_income_trends.csv", index=False)
    date_frame.to_csv(output_dir / "check_in_date_income_trends.csv", index=False)
    context_frame.to_csv(output_dir / "monthly_context_trends.csv", index=False)

    _render_chart(
        monthly_frame,
        x_column="month_label",
        y_column="reservations",
        title="Monthly Reservations by Room",
        y_label="Reservations",
        output_path=output_dir / "monthly_reservations_by_room.png",
    )
    _render_chart(
        monthly_frame,
        x_column="month_label",
        y_column="gross_income_sum",
        title="Monthly Gross Income by Room",
        y_label="Gross income",
        output_path=output_dir / "monthly_gross_income_by_room.png",
    )
    _render_chart(
        monthly_frame,
        x_column="month_label",
        y_column="median_gross_adr",
        title="Monthly Median ADR by Room",
        y_label="Median gross ADR",
        output_path=output_dir / "monthly_median_adr_by_room.png",
    )
    _render_context_chart(context_frame, output_dir / "monthly_context_adr.png")

    summary_output = output_dir / "income_trend_summary.json"
    summary_output.write_text(
        json.dumps(visual_summary, indent=2, ensure_ascii=True, default=str),
        encoding="utf-8",
    )

    markdown_output = output_dir / "income_trend_summary.md"
    markdown_output.write_text(
        _render_markdown_report(dataset.source_path.name, visual_summary, monthly_frame),
        encoding="utf-8",
    )

    preview = {
        "source": str(dataset.source_path),
        "output_dir": str(output_dir),
        "rows": int(len(analysis_table)),
        "currencies": visual_summary["summary_scope"]["currencies"],
        "units": visual_summary["summary_scope"]["units"],
    }
    print(json.dumps(preview, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
