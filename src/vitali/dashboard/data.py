"""Data loading helpers shared by the Streamlit app and the static report."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from vitali.models.baseline_heuristic import BaselineHeuristicRules

_REPO_ROOT = Path(__file__).resolve().parents[3]

UNIT_LABELS = {"room_a": "CieloRosa", "room_b": "Aqua"}
MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def repo_root() -> Path:
    return _REPO_ROOT


def load_reservations(root: Path | None = None) -> pd.DataFrame:
    root = root or _REPO_ROOT
    path = root / "data" / "interim" / "income_reservations_fx_crc_interim.parquet"
    df = pd.read_parquet(path)
    df = df[df["record_type"] == "reservation"].copy()
    df["check_in"] = pd.to_datetime(df["check_in"], errors="coerce")
    df["unit_label"] = df["unit_id"].map(UNIT_LABELS)
    return df


def load_monthly_trends(root: Path | None = None) -> pd.DataFrame:
    root = root or _REPO_ROOT
    path = root / "artifacts" / "income_trends" / "tables" / "monthly_income_trends.csv"
    df = pd.read_csv(path)
    df["month_start"] = pd.to_datetime(df["month_start"])
    return df


def load_rolling_metrics(root: Path | None = None) -> dict:
    root = root or _REPO_ROOT
    path = root / "artifacts" / "evaluation" / "phase6_rolling_metrics.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_phase5_metrics(root: Path | None = None) -> dict:
    root = root or _REPO_ROOT
    path = root / "artifacts" / "baseline" / "phase5_metrics.json"
    return json.loads(path.read_text(encoding="utf-8"))


def fit_baseline_all_data(df: pd.DataFrame) -> BaselineHeuristicRules:
    """Fit baseline on all available reservations (for pricing reference tool)."""
    return BaselineHeuristicRules().fit(df)


def pricing_reference(
    model: BaselineHeuristicRules,
    df: pd.DataFrame,
    *,
    unit_id: str,
    month: int,
    is_weekend: int,
    currency: str,
) -> dict:
    """Return model prediction + historical distribution for a given segment."""
    seg = df[
        (df["unit_id"] == unit_id)
        & (df["check_in_month"] == month)
        & (df["currency"] == currency)
    ].copy()

    y_seg = (
        seg["gross_income"].astype(float) / seg["nights"].replace({0: np.nan}).astype(float)
    ).dropna()

    if currency == "CRC":
        query_row = pd.DataFrame([{
            "unit_id": unit_id,
            "check_in_month": month,
            "is_weekend": is_weekend,
            "currency": currency,
        }])
        pred = float(model.predict(query_row).iloc[0])
    else:
        pred = float("nan")

    hist: dict = {}
    if len(y_seg) > 0:
        hist = {
            "n": int(len(y_seg)),
            "p25": float(y_seg.quantile(0.25)),
            "median": float(y_seg.median()),
            "p75": float(y_seg.quantile(0.75)),
            "min": float(y_seg.min()),
            "max": float(y_seg.max()),
        }

    return {
        "unit_id": unit_id,
        "unit_label": UNIT_LABELS.get(unit_id, unit_id),
        "month": month,
        "month_name": MONTH_NAMES.get(month, str(month)),
        "is_weekend": is_weekend,
        "currency": currency,
        "model_pred_adr": pred,
        "model_reliable": currency == "CRC",
        "historical": hist,
    }
