"""Minimal Phase 2 pipeline: load expenses + income, validate, monthly reconciliation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from vitali.data.loaders import load_expenses, load_income_fx
from vitali.data.validators import DataQualityReport, validate_pipeline_inputs


def load_validate_reconcile(
    root: Path | None = None,
    *,
    expense_years: tuple[int, ...] = (2025, 2026),
    min_check_in_year: int | None = 2025,
) -> tuple[pd.DataFrame, pd.DataFrame, DataQualityReport, pd.DataFrame]:
    """Load expenses (all requested years), income FX table, validate, return reconciliation."""
    exp_parts = [load_expenses(y, root) for y in expense_years]
    expenses = pd.concat(exp_parts, ignore_index=True) if exp_parts else pd.DataFrame()
    income = load_income_fx(root, min_check_in_year=min_check_in_year)
    report = validate_pipeline_inputs(expenses, income)
    recon = reconcile_monthly(expenses, income) if report.is_valid else pd.DataFrame()
    return expenses, income, report, recon


def reconcile_monthly(expenses: pd.DataFrame, income: pd.DataFrame) -> pd.DataFrame:
    """Monthly sums: gross income CRC (by check-in month) minus expense CRC (by fecha month)."""
    exp = expenses.dropna(subset=["fecha"]).copy()
    exp["period"] = exp["fecha"].dt.to_period("M")
    exp_sum = exp.groupby("period", sort=True)["monto_crc"].sum().rename("egresos_crc")

    inc = income.dropna(subset=["check_in"]).copy()
    inc["period"] = inc["check_in"].dt.to_period("M")
    inc_sum = inc.groupby("period", sort=True).agg(
        ingresos_gross_crc=("gross_income_crc", "sum"),
        ingresos_net_crc=("net_amount_crc", "sum"),
        n_bookings=("gross_income_crc", "count"),
    )

    out = inc_sum.join(exp_sum, how="outer").fillna(
        {"ingresos_gross_crc": 0.0, "ingresos_net_crc": 0.0, "n_bookings": 0, "egresos_crc": 0.0}
    )
    out["egresos_crc"] = out["egresos_crc"].fillna(0.0)
    out["neto_gross_menos_egresos_crc"] = out["ingresos_gross_crc"] - out["egresos_crc"]
    out["neto_net_menos_egresos_crc"] = out["ingresos_net_crc"] - out["egresos_crc"]
    out = out.reset_index()
    out["year"] = out["period"].dt.year
    out["month"] = out["period"].dt.month
    return out
