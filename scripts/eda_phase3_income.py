"""Phase 3 descriptive EDA on sanitized income reservations (Yellow gate).

Loads `data/sanitized/income_reservations_fx_crc_sanitized.parquet` (run
`uv run python scripts/prepare_phase3_datasets.py` first).

Usage:
    uv run python scripts/eda_phase3_income.py
    uv run python scripts/eda_phase3_income.py --root /path/to/proyecto-vitali

Outputs under `artifacts/eda/` (CSVs + PNG). Findings and interpretation live in
`research/04_eda_findings.md` (vault), not in this script.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3 income EDA (descriptive).")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repo root (default: cwd)")
    args = parser.parse_args()
    root: Path = args.root.resolve()

    inp = root / "data" / "sanitized" / "income_reservations_fx_crc_sanitized.parquet"
    if not inp.is_file():
        raise SystemExit(f"Missing {inp}; run scripts/prepare_phase3_datasets.py first.")

    out = root / "artifacts" / "eda"
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(inp)
    df = df.loc[df["record_type"] == "reservation"].copy()
    df["check_in"] = pd.to_datetime(df["check_in"], errors="coerce")
    df["gross_adr_native"] = df["gross_income"] / df["nights"].replace({0: pd.NA})

    meta = {
        "input": str(inp),
        "reservation_rows": int(len(df)),
        "currencies": sorted(df["currency"].dropna().unique().tolist()),
    }
    (out / "eda_run_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # --- Tabular summaries (never mix USD and CRC amounts in one numeric column) ---
    by_unit_curr = (
        df.dropna(subset=["gross_adr_native"])
        .groupby(["currency", "unit_id"], dropna=False)["gross_adr_native"]
        .agg(count="count", median="median", q25=lambda s: s.quantile(0.25), q75=lambda s: s.quantile(0.75))
        .reset_index()
    )
    by_unit_curr.to_csv(out / "adr_native_by_unit_currency.csv", index=False)

    wk = (
        df.dropna(subset=["gross_adr_native", "is_weekend"])
        .groupby(["currency", "is_weekend"], dropna=False)["gross_adr_native"]
        .agg(median="median", count="count")
        .reset_index()
    )
    wk.to_csv(out / "adr_native_median_by_currency_weekend.csv", index=False)

    df["check_in_month"] = df["check_in"].dt.month
    monthly = df.groupby(["currency", "check_in_month"], dropna=False).size().reset_index(name="reservations")
    monthly.to_csv(out / "reservation_counts_by_currency_checkin_month.csv", index=False)

    if "lead_bucket" in df.columns:
        lb = df.groupby(["currency", "lead_bucket"], dropna=False).size().reset_index(name="count")
        lb.to_csv(out / "lead_bucket_counts_by_currency.csv", index=False)

    if "fx_normalization_status" in df.columns:
        fxst = df.groupby(["currency", "fx_normalization_status"], dropna=False).size().reset_index(name="count")
        fxst.to_csv(out / "fx_normalization_status_by_currency.csv", index=False)

    # --- Figures: one currency per file (scales differ) ---
    for cur in df["currency"].dropna().unique():
        sub = df.loc[df["currency"] == cur].copy()
        if sub.empty:
            continue
        cur_slug = str(cur).lower()
        fig, ax = plt.subplots(figsize=(8, 4))
        sub.boxplot(column="gross_adr_native", by="unit_id", ax=ax)
        ax.set_title(f"Gross ADR ({cur} per night, listing currency) by unit_id")
        ax.set_xlabel("unit_id")
        ax.set_ylabel(f"ADR ({cur})")
        plt.suptitle("")
        fig.tight_layout()
        fig.savefig(out / f"box_gross_adr_native_by_unit_{cur_slug}.png", dpi=120)
        plt.close(fig)

        fig2, ax2 = plt.subplots(figsize=(7, 4))
        pivot = (
            sub.dropna(subset=["check_in_month"])
            .groupby("check_in_month")
            .size()
            .reindex(range(1, 13), fill_value=0)
        )
        ax2.bar(pivot.index.astype(int), pivot.values, color="steelblue")
        ax2.set_title(f"Reservation count by check-in month ({cur})")
        ax2.set_xlabel("check_in month")
        ax2.set_ylabel("count")
        fig2.tight_layout()
        fig2.savefig(out / f"hist_reservations_by_checkin_month_{cur_slug}.png", dpi=120)
        plt.close(fig2)

    # Optional: CRC-normalized ADR for USD rows (second axis / separate fig — only for cross-check)
    if "gross_adr_crc" in df.columns:
        sub_crc_metric = df.dropna(subset=["gross_adr_crc", "unit_id"])
        if not sub_crc_metric.empty:
            fig3, ax3 = plt.subplots(figsize=(8, 4))
            sub_crc_metric.boxplot(column="gross_adr_crc", by="unit_id", ax=ax3)
            ax3.set_title("Gross ADR (CRC per night, fx-normalized) by unit_id — all currencies in CRC space")
            ax3.set_xlabel("unit_id")
            ax3.set_ylabel("ADR (CRC)")
            plt.suptitle("")
            fig3.tight_layout()
            fig3.savefig(out / "box_gross_adr_crc_normalized_by_unit.png", dpi=120)
            plt.close(fig3)

    print(f"EDA artifacts written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
