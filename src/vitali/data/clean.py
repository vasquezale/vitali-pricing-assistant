"""Phase 3 data preparation: deterministic cleaning and safe feature generation.

This module produces intermediate datasets for the Yellow gate path:
- no per-reservation profitability claims,
- no mixing CRC/USD without an explicit policy,
- treat `resolution_payment` as a ledger row, not as a reservation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from vitali.config import IncomeDataConfig
from vitali.data.income import load_income_data
from vitali.data.loaders import load_expenses, load_income_fx


@dataclass(frozen=True)
class PreparedIncome:
    """Income tables prepared for EDA and heuristic rules."""

    reservations_fx_crc: pd.DataFrame
    ledger_resolution_payments: pd.DataFrame


def prepare_income_from_raw_airbnb(
    root: Path | None = None,
    *,
    config: IncomeDataConfig | None = None,
) -> PreparedIncome:
    """Prepare income from the canonical anonymized Airbnb extract in `data/raw/airbnb/`.

    Returns:
    - reservations_fx_crc: reservation rows joined to FX-derived CRC columns from
      `artifacts/income_analysis_table_fx.csv` (by check_in + unit_id + currency + nights + gross_income).
    - ledger_resolution_payments: resolution_payment rows, kept separate.
    """
    base = Path.cwd() if root is None else Path(root)
    cfg = config or IncomeDataConfig()
    raw_path = base / cfg.source_file
    ds = load_income_data(raw_path, cfg)
    raw = ds.records.copy()

    reservations = raw.loc[raw["record_type"] == "reservation"].copy()
    ledger = raw.loc[raw["record_type"] == "resolution_payment"].copy()

    # Add safe calendar features for reservations.
    reservations["check_in_year"] = reservations["check_in"].dt.year
    reservations["check_in_month"] = reservations["check_in"].dt.month
    reservations["check_in_dow"] = reservations["check_in"].dt.dayofweek
    reservations["is_weekend"] = reservations["check_in_dow"].isin([4, 5]).astype(int)

    fx = load_income_fx(base, min_check_in_year=None).copy()
    fx["check_in"] = pd.to_datetime(fx["check_in"], errors="coerce")

    join_keys = ["check_in", "unit_id", "currency", "nights", "gross_income"]
    fx_cols = [
        "gross_income_crc",
        "net_amount_crc",
        "gross_adr_crc",
        "net_adr_crc",
        "fx_rate_to_crc",
        "fx_normalization_status",
        "booking_lead_days",
        "lead_bucket",
        "check_in_context",
        "check_in_weekday",
    ]
    # Raw extract already includes booking_lead_days; FX table repeats it — merge once from reservations.
    if "booking_lead_days" in reservations.columns:
        fx_cols = [c for c in fx_cols if c != "booking_lead_days"]
    fx_small = fx[join_keys + [c for c in fx_cols if c in fx.columns]].drop_duplicates()

    merged = reservations.merge(fx_small, on=join_keys, how="left", validate="many_to_one")

    # For pipeline safety, keep ledger rows completely separated.
    return PreparedIncome(reservations_fx_crc=merged, ledger_resolution_payments=ledger)


def prepare_expenses(
    root: Path | None = None,
    *,
    years: tuple[int, ...] = (2025, 2026),
) -> pd.DataFrame:
    """Prepare expenses with minimal normalization and a guarded bucket label."""
    base = Path.cwd() if root is None else Path(root)
    frames = [load_expenses(y, base) for y in years]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # Basic normalization
    df["descripcion"] = df["descripcion"].astype("string")
    df["pagado_por"] = df["pagado_por"].astype("string")

    # Guarded bucket based on keywords only; it is NOT an accounting taxonomy.
    desc = df["descripcion"].fillna("").str.upper()
    operativo = desc.str.contains(
        r"STARLINK|INTERNET|JASEC|ELECTRIC|LUZ|AGUA|LIMPIEZA|MANTENIMIENTO|JARDIN|BASURA|CONTAB|BAC|BANCO",
        regex=True,
    )
    posible_capex = desc.str.contains(r"MUEBLE|DECOR|CONSTRU|REMODEL|EQUIPO", regex=True)
    df["expense_bucket"] = "ambiguo"
    df.loc[operativo, "expense_bucket"] = "operativo_defendible"
    df.loc[posible_capex, "expense_bucket"] = "posible_capex"

    return df


def write_phase3_outputs(
    prepared: PreparedIncome,
    expenses: pd.DataFrame,
    *,
    root: Path | None = None,
) -> dict[str, Path]:
    """Write deterministic intermediate outputs under data/sanitized and data/interim."""
    base = Path.cwd() if root is None else Path(root)
    sanitized = base / "data" / "sanitized"
    interim = base / "data" / "interim"
    sanitized.mkdir(parents=True, exist_ok=True)
    interim.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}

    p1 = sanitized / "income_reservations_fx_crc_sanitized.parquet"
    prepared.reservations_fx_crc.to_parquet(p1, index=False)
    paths["income_reservations_fx_crc_sanitized"] = p1

    p2 = sanitized / "income_resolution_payments_ledger.parquet"
    prepared.ledger_resolution_payments.to_parquet(p2, index=False)
    paths["income_resolution_payments_ledger"] = p2

    p3 = interim / "expenses_all_years_interim.parquet"
    expenses.to_parquet(p3, index=False)
    paths["expenses_all_years_interim"] = p3

    return paths

