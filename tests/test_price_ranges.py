from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from vitali.mvp.price_ranges import (
    PRICE_RANGES_PATH,
    PROHIBITED_TERMS,
    PriceRangeEvaluationError,
    evaluate_price,
    load_price_ranges,
)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_load_price_ranges_dataset_contract(repo_root) -> None:
    df = load_price_ranges(repo_root=repo_root)
    assert not df.empty
    assert sorted(df["unit_id"].unique().tolist()) == ["room_a", "room_b"]
    assert set(df["month"].dropna().astype(int).tolist()) == set(range(1, 13))
    assert set(df["is_weekend"].astype(bool).unique().tolist()) == {False, True}


def test_evaluate_price_room_a_below_range(repo_root) -> None:
    result = evaluate_price("room_a", 2, "weekend", 65000, repo_root=repo_root)
    assert result["room_label"] == "CieloRosa"
    assert result["price_position"] == "por_debajo"
    assert result["range_low_crc"] == 70000.0
    assert result["reference_price_crc"] == 77000.0
    assert result["range_high_crc"] == 90000.0


def test_evaluate_price_room_b_within_range(repo_root) -> None:
    df = load_price_ranges(repo_root=repo_root)
    segment = df[(df["unit_id"] == "room_b") & (df["month"] == 1) & (df["is_weekend"])]
    row = segment.iloc[0]
    result = evaluate_price("room_b", 1, "weekend", float(row["adr_median_crc"]), repo_root=repo_root)
    assert result["room_label"] == "Aqua"
    assert result["price_position"] == "dentro_del_rango"
    assert result["confidence_label"] in {"baja", "media", "alta"}


def test_evaluate_price_room_b_above_range(repo_root) -> None:
    df = load_price_ranges(repo_root=repo_root)
    segment = df[(df["unit_id"] == "room_b") & (df["month"] == 1) & (~df["is_weekend"])]
    row = segment.iloc[0]
    result = evaluate_price(
        "room_b",
        1,
        "weekday",
        float(row["adr_p75_crc"]) + 1000.0,
        repo_root=repo_root,
    )
    assert result["price_position"] == "por_encima"


@pytest.mark.parametrize(
    ("unit_id", "month", "day_type", "price"),
    [
        ("room_x", 1, "weekday", 50000),
        ("room_a", 13, "weekday", 50000),
        ("room_a", 1, "midweek", 50000),
        ("room_a", 1, "weekday", -1),
    ],
)
def test_evaluate_price_invalid_inputs_raise(
    repo_root,
    unit_id: str,
    month: int,
    day_type: str,
    price: float,
) -> None:
    with pytest.raises(PriceRangeEvaluationError):
        evaluate_price(unit_id, month, day_type, price, repo_root=repo_root)


def test_evaluate_price_segment_without_data_raises(tmp_path) -> None:
    df = pd.DataFrame(
        [
            {
                "unit_id": "room_a",
                "unit_display_name": "CieloRosa",
                "month": 1,
                "is_weekend": True,
                "adr_p25_crc": 60000.0,
                "adr_median_crc": 70000.0,
                "adr_p75_crc": 80000.0,
                "trend": "estable",
                "confidence": "media",
                "confidence_reason": "Soporte moderado",
                "n_reservations": 8,
                "usd_context_only": False,
            }
        ]
    )
    dataset_path = tmp_path / "minimal.parquet"
    df.to_parquet(dataset_path, index=False)

    with pytest.raises(PriceRangeEvaluationError, match="sin_referencia_suficiente"):
        evaluate_price("room_a", 2, "weekday", 70000.0, dataset_path=dataset_path)


def test_load_price_ranges_rejects_missing_columns(tmp_path) -> None:
    df = pd.DataFrame([{"unit_id": "room_a", "month": 1}])
    dataset_path = tmp_path / "broken.parquet"
    df.to_parquet(dataset_path, index=False)

    with pytest.raises(PriceRangeEvaluationError, match="Faltan columnas requeridas"):
        load_price_ranges(dataset_path=dataset_path)


def test_message_avoids_prohibited_language(repo_root) -> None:
    result = evaluate_price("room_a", 1, "weekday", 61000, repo_root=repo_root)
    lowered = result["message"].lower()
    for term in PROHIBITED_TERMS:
        assert term not in lowered


def test_usd_only_used_as_context_warning(repo_root) -> None:
    result = evaluate_price("room_a", 1, "weekday", 61000, repo_root=repo_root)
    assert "USD" not in result["message"]
    if result["uses_usd_context_only"]:
        assert any("USD" in warning for warning in result["warnings"])


def test_price_ranges_path_contract_is_stable() -> None:
    assert PRICE_RANGES_PATH.as_posix() == "data/processed/f7_capa1_price_ranges.parquet"
