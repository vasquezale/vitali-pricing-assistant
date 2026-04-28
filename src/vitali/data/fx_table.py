"""Producer utilities for the canonical FX income table.

This module formalizes how to build `artifacts/income_analysis_table_fx.csv`
from the anonymized raw income extract, using explicit FX rates.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from vitali.config import Config
from vitali.contracts.artifacts import REQUIRED_INCOME_FX_COLUMNS
from vitali.data.income import build_income_analysis_table, load_income_data


def build_income_analysis_table_fx(
    *,
    repo_root: str | Path,
    input_csv: str | Path,
    config: Config,
    fx_rates_to_crc: dict[str, float],
    output_csv: str | Path,
) -> Path:
    """Generate an FX-normalized income analysis table and write it to `output_csv`.

    The table is expected to be fully normalized for all currencies present.
    """
    root = Path(repo_root).resolve()
    out_path = (root / output_csv).resolve() if not Path(output_csv).is_absolute() else Path(output_csv).resolve()

    dataset = load_income_data(Path(input_csv), config.income_data)
    records = dataset.records

    currencies = sorted(set(records["currency"].dropna().unique().tolist()))
    missing_rates = sorted(set(currencies) - set(fx_rates_to_crc.keys()))
    if missing_rates:
        raise ValueError(f"FX rates missing for currencies: {', '.join(missing_rates)}")

    table = build_income_analysis_table(records, fx_rates_to_crc=fx_rates_to_crc)
    missing_cols = sorted(set(REQUIRED_INCOME_FX_COLUMNS) - set(table.columns))
    if missing_cols:
        raise ValueError(f"Output table missing required columns: {', '.join(missing_cols)}")

    bad = table.loc[table["fx_normalization_status"] != "normalized_to_crc"]
    if not bad.empty:
        raise ValueError(
            "FX normalization incomplete: output contains rows not normalized_to_crc. "
            "Provide rates for all currencies."
        )

    if table["gross_income_crc"].isna().all():
        raise ValueError("FX normalization produced null gross_income_crc for all rows.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_path, index=False)
    return out_path

