"""Prepare Phase 3 intermediate datasets (Yellow gate path).

Usage:
    uv run python scripts/prepare_phase3_datasets.py
"""

from __future__ import annotations

from pathlib import Path

from vitali.data.clean import prepare_expenses, prepare_income_from_raw_airbnb, write_phase3_outputs
from vitali.data.pipeline import reconcile_monthly
from vitali.data.validators import validate_pipeline_inputs


def main() -> int:
    root = Path.cwd()
    prepared_income = prepare_income_from_raw_airbnb(root)
    expenses = prepare_expenses(root)

    report = validate_pipeline_inputs(expenses, prepared_income.reservations_fx_crc)

    print("=== Phase 3: preparation summary ===")
    print(f"Income reservations rows: {len(prepared_income.reservations_fx_crc)}")
    print(f"Income ledger (resolution_payment) rows: {len(prepared_income.ledger_resolution_payments)}")
    print(f"Expenses rows: {len(expenses)}")
    if report.errors:
        print("Errors:")
        for e in report.errors:
            print(f"- {e}")
    if report.alerts:
        print("Alerts:")
        for a in report.alerts:
            print(f"- {a}")

    out_paths = write_phase3_outputs(prepared_income, expenses, root=root)
    print("Outputs:")
    for k, p in sorted(out_paths.items()):
        print(f"- {k}: {p}")

    # Monthly view (indicative)
    recon = reconcile_monthly(expenses, prepared_income.reservations_fx_crc)
    recon_path = root / "data" / "interim" / "reconcile_monthly_indicative.parquet"
    recon.to_parquet(recon_path, index=False)
    print(f"- reconcile_monthly_indicative: {recon_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

