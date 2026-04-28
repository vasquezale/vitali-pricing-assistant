"""Load expense workbooks and FX-normalized income table for Phase 2 pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from vitali.config import ExpenseDataConfig
from vitali.contracts.artifacts import ARTIFACTS, REQUIRED_INCOME_FX_COLUMNS
from vitali.data.expenses import load_expense_data

MONTH_SHEETS_12 = [
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
]


def project_root(root: Path | None = None) -> Path:
    """Resolve project root (directory that contains `data/` and `artifacts/`)."""
    if root is not None:
        return root.resolve()
    return Path.cwd().resolve()


def expenses_workbook_path(year: int, root: Path | None = None) -> Path:
    """Path to raw expense XLSX for a calendar year (see `data/raw/DATA_MANIFEST.md`)."""
    base = project_root(root)
    return base / "data" / "raw" / str(year) / f"expenses_{year}_raw.xlsx"


def expense_config_for_year(year: int) -> ExpenseDataConfig:
    """Build `ExpenseDataConfig` for the versioned `expenses_{year}_raw.xlsx` layout."""
    name = f"expenses_{year}_raw.xlsx"
    if year == 2025:
        sheets = MONTH_SHEETS_12
    elif year == 2026:
        sheets = ["ENERO", "FEBRERO", "MARZO"]
    else:
        raise ValueError(f"Unsupported expense year for pipeline: {year}")

    return ExpenseDataConfig(
        source_files=[f"data/raw/{year}/{name}"],
        expected_sheet_names_by_file={name: sheets},
    )


def load_expenses(year: int, root: Path | None = None) -> pd.DataFrame:
    """Load all expense rows from the canonical XLSX for `year` (full intake, no business filter)."""
    base = project_root(root)
    path = expenses_workbook_path(year, base)
    if not path.is_file():
        raise FileNotFoundError(f"Expense workbook not found: {path}")

    cfg = expense_config_for_year(year)
    paths = [base / rel for rel in cfg.source_files]
    dataset = load_expense_data(paths, cfg)
    df = dataset.records.copy()
    df.rename(
        columns={
            "expense_date": "fecha",
            "description": "descripcion",
            "paid_by": "pagado_por",
            "amount_crc": "monto_crc",
        },
        inplace=True,
    )
    df["expense_year"] = df["fecha"].dt.year
    df["expense_month"] = df["fecha"].dt.month
    return df


def income_fx_csv_path(root: Path | None = None) -> Path:
    """Path to `artifacts/income_analysis_table_fx.csv` (FX-normalized income table)."""
    base = project_root(root)
    return base / ARTIFACTS.income_analysis_table_fx_csv


def load_income_fx(
    root: Path | None = None,
    *,
    min_check_in_year: int | None = 2025,
) -> pd.DataFrame:
    """Load the FX table used for monthly income in CRC (see `data/raw/DATA_MANIFEST.md`)."""
    path = income_fx_csv_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"Income FX table not found: {path}")

    df = pd.read_csv(path)
    missing = sorted(set(REQUIRED_INCOME_FX_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Income FX CSV missing columns: {', '.join(missing)}")

    df = df.copy()
    df["check_in"] = pd.to_datetime(df["check_in"], errors="coerce")
    for col in ("gross_income_crc", "net_amount_crc"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["check_in_year"] = df["check_in"].dt.year
    df["check_in_month"] = df["check_in"].dt.month

    if min_check_in_year is not None:
        df = df.loc[df["check_in_year"] >= min_check_in_year].copy()

    return df
