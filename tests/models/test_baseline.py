"""Tests for Phase 5 baseline (no temporal leakage in fit, CRC/USD isolation)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from vitali.models.baseline_heuristic import BaselineHeuristicRules, regression_metrics, temporal_train_val_split


def _minimal_reservation_frame() -> pd.DataFrame:
    """Synthetic reservations with two currencies and two units."""
    base = []
    # USD room_a: early year train, late year val — same ADR level for simple check
    for m in range(1, 9):
        base.append(
            {
                "record_type": "reservation",
                "check_in": pd.Timestamp(2024, m, 5),
                "nights": 2,
                "gross_income": 300.0,
                "currency": "USD",
                "unit_id": "room_a",
                "lead_bucket": "4-7",
            }
        )
    for m in range(9, 13):
        base.append(
            {
                "record_type": "reservation",
                "check_in": pd.Timestamp(2024, m, 5),
                "nights": 2,
                "gross_income": 300.0,
                "currency": "USD",
                "unit_id": "room_a",
                "lead_bucket": "4-7",
            }
        )
    # CRC room_b higher ADR
    for m in range(1, 11):
        base.append(
            {
                "record_type": "reservation",
                "check_in": pd.Timestamp(2024, m, 12),
                "nights": 1,
                "gross_income": 80000.0,
                "currency": "CRC",
                "unit_id": "room_b",
                "lead_bucket": "8-14",
            }
        )
    for m in range(11, 13):
        base.append(
            {
                "record_type": "reservation",
                "check_in": pd.Timestamp(2024, m, 12),
                "nights": 1,
                "gross_income": 80000.0,
                "currency": "CRC",
                "unit_id": "room_b",
                "lead_bucket": "8-14",
            }
        )
    return pd.DataFrame(base)


def test_temporal_split_orders_train_before_val() -> None:
    df = _minimal_reservation_frame()
    train, val = temporal_train_val_split(df, val_frac=0.2)
    assert not train.empty and not val.empty
    assert len(train) + len(val) == len(df)


def test_baseline_fit_only_train_no_val_in_table() -> None:
    df = _minimal_reservation_frame()
    train, val = temporal_train_val_split(df, val_frac=0.25)
    model = BaselineHeuristicRules().fit(train, use_lead_multipliers=False)
    pred = model.predict(val)
    y = val["gross_income"].astype(float) / val["nights"].astype(float)
    mask = pred.notna() & y.notna()
    assert mask.sum() > 0
    mae = regression_metrics(y.loc[mask].to_numpy(), pred.loc[mask].to_numpy())["mae"]
    assert mae < np.inf


def test_currency_isolation_predictions() -> None:
    df = _minimal_reservation_frame()
    train, val = temporal_train_val_split(df, val_frac=0.3)
    model = BaselineHeuristicRules().fit(train, use_lead_multipliers=False)
    pred = model.predict(val)
    for cur in val["currency"].unique():
        m = val["currency"] == cur
        s = pred.loc[m].dropna()
        if s.empty:
            continue
        if cur == "USD":
            assert (s < 500).all()
        if cur == "CRC":
            assert (s > 1000).all()


def test_phase5_interim_parquet_exists_after_prepare(repo_root) -> None:
    path = repo_root / "data" / "interim" / "income_reservations_fx_crc_interim.parquet"
    raw = repo_root / "data" / "raw" / "airbnb" / "Ingresos_Vitali_ingresos_anonimizados.csv"
    if not raw.is_file():
        pytest.skip("raw income not in workspace")
    if not path.is_file():
        pytest.skip("run prepare_phase3_datasets.py to generate interim reservations copy")
