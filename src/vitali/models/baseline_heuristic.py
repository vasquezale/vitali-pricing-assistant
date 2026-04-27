"""Calendar + unit baseline for nightly gross ADR (listing currency only).

Uses only leakage-safe inputs documented as **Sí** ex-ante in research/03:
`currency`, `unit_id`, `check_in_month`, `is_weekend`.

Optional `lead_bucket` adjustment is **off** by default (not ex-ante); enable only
for the explicit "booking-day" backtest scenario.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """MAE and MAPE (%); MAPE ignores zero targets."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_true - y_pred
    mae = float(np.mean(np.abs(err)))
    denom = np.where(np.abs(y_true) < 1e-12, np.nan, np.abs(y_true))
    mape = float(np.nanmean(np.abs(err / denom)) * 100.0)
    return {"mae": mae, "mape_pct": mape}


def _adr_native(df: pd.DataFrame) -> pd.Series:
    return df["gross_income"].astype(float) / df["nights"].replace({0: np.nan}).astype(float)


def _temporal_train_val_single_currency(
    d: pd.DataFrame,
    *,
    val_frac: float,
    date_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = d.dropna(subset=[date_col]).sort_values(date_col)
    dates = np.sort(d[date_col].unique())
    if len(dates) < 5 or len(d) < 15:
        n_val = max(1, int(len(d) * val_frac))
        val = d.iloc[-n_val:]
        train = d.iloc[:-n_val]
        return train, val
    n_val_dates = max(1, int(len(dates) * val_frac))
    threshold = pd.Timestamp(dates[-n_val_dates])
    train = d[d[date_col] < threshold]
    val = d[d[date_col] >= threshold]
    if train.empty or val.empty:
        n_val = max(1, int(len(d) * val_frac))
        val = d.iloc[-n_val:]
        train = d.iloc[:-n_val]
    return train, val


def temporal_train_val_split(
    df: pd.DataFrame,
    *,
    val_frac: float = 0.2,
    date_col: str = "check_in",
    stratify_currency: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Time-ordered split on `date_col`.

    If `stratify_currency` and `currency` exists, split each currency separately
    so validation still contains CRC and USD when each is present in the input.
    """
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    if stratify_currency and "currency" in d.columns:
        trains, vals = [], []
        for _, g in d.groupby("currency", dropna=False):
            if len(g) < 3:
                trains.append(g)
                continue
            tr, va = _temporal_train_val_single_currency(g, val_frac=val_frac, date_col=date_col)
            trains.append(tr)
            vals.append(va)
        train = pd.concat(trains, ignore_index=True) if trains else d.iloc[0:0]
        val = pd.concat(vals, ignore_index=True) if vals else d.iloc[0:0]
        return train, val
    return _temporal_train_val_single_currency(d, val_frac=val_frac, date_col=date_col)


def _ensure_calendar(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "check_in" in out.columns:
        out["check_in"] = pd.to_datetime(out["check_in"], errors="coerce")
    if "check_in_month" not in out.columns and "check_in" in out.columns:
        out["check_in_month"] = out["check_in"].dt.month
    if "is_weekend" not in out.columns and "check_in" in out.columns:
        dow = out["check_in"].dt.dayofweek
        out["is_weekend"] = dow.isin([4, 5]).astype(int)
    return out


def _lookup_group_median(series: pd.Series, keys: list[str], row: pd.Series) -> float:
    """Fetch median from a groupby result; index may be MultiIndex or scalar per arity."""
    if len(keys) == 1:
        k = row[keys[0]]
        if k not in series.index:
            return float("nan")
        return float(series.loc[k])
    k = tuple(row[c] for c in keys)
    if k not in series.index:
        return float("nan")
    return float(series.loc[k])


@dataclass
class BaselineHeuristicRules:
    """Hierarchical median ADR lookup fit on a training frame only."""

    tables: dict[str, pd.Series] = field(default_factory=dict)
    lead_multipliers: dict[tuple[Any, Any], float] | None = None

    def fit(
        self,
        train: pd.DataFrame,
        *,
        use_lead_multipliers: bool = False,
    ) -> BaselineHeuristicRules:
        """Fit medians on `train` only. `train` must include reservation rows."""
        train = _ensure_calendar(train.loc[train["record_type"] == "reservation"].copy())
        train["_y"] = _adr_native(train)

        keys_levels = [
            ["currency", "unit_id", "check_in_month", "is_weekend"],
            ["currency", "unit_id", "is_weekend"],
            ["currency", "unit_id"],
            ["currency"],
        ]
        self.tables = {}
        for i, keys in enumerate(keys_levels, start=1):
            self.tables[f"L{i}"] = train.groupby(keys, dropna=False)["_y"].median()

        self.lead_multipliers = None
        if use_lead_multipliers and "lead_bucket" in train.columns:
            base = train.groupby(["currency"], dropna=False)["_y"].median()
            by_lead = train.groupby(["currency", "lead_bucket"], dropna=False)["_y"].median()
            mult: dict[tuple[Any, Any], float] = {}
            for (cur, bucket), med in by_lead.items():
                denom = float(base.loc[cur]) if cur in base.index and pd.notna(base.loc[cur]) else np.nan
                if pd.notna(med) and pd.notna(denom) and denom > 0:
                    mult[(cur, bucket)] = float(med) / denom
                else:
                    mult[(cur, bucket)] = 1.0
            self.lead_multipliers = mult

        return self

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """Return predicted gross ADR in listing currency (aligned to df index)."""
        df = _ensure_calendar(df.copy())
        keys_levels = [
            ["currency", "unit_id", "check_in_month", "is_weekend"],
            ["currency", "unit_id", "is_weekend"],
            ["currency", "unit_id"],
            ["currency"],
        ]
        preds: list[float] = []
        for _, row in df.iterrows():
            val = float("nan")
            for i, level in enumerate(keys_levels, start=1):
                series = self.tables.get(f"L{i}")
                if series is None:
                    continue
                got = _lookup_group_median(series, level, row)
                if not np.isnan(got):
                    val = got
                    break
            preds.append(val)
        out = pd.Series(preds, index=df.index, dtype=float)

        if self.lead_multipliers and "lead_bucket" in df.columns:
            for idx, row in df.iterrows():
                k = (row["currency"], row["lead_bucket"])
                m = self.lead_multipliers.get(k, 1.0)
                if pd.notna(out.loc[idx]):
                    out.loc[idx] = float(out.loc[idx]) * float(m)
        return out
