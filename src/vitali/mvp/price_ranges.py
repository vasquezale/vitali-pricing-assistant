"""Phase 7 MVP price range evaluator for room-level operational guidance."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
PRICE_RANGES_PATH = Path("data/processed/f7_capa1_price_ranges.parquet")
ALLOWED_UNIT_IDS = {"room_a", "room_b"}
ALLOWED_DAY_TYPES = {"weekday": False, "weekend": True}
PROHIBITED_TERMS = (
    "precio óptimo",
    "precio optimo",
    "precio exacto",
    "maximización automática",
    "maximizacion automatica",
    "decisión automática",
    "decision automatica",
    "el sistema recomienda cobrar",
    "rentabilidad garantizada",
)
REQUIRED_COLUMNS = [
    "unit_id",
    "unit_display_name",
    "month",
    "is_weekend",
    "adr_p25_crc",
    "adr_median_crc",
    "adr_p75_crc",
    "trend",
    "confidence",
    "confidence_reason",
    "n_reservations",
    "usd_context_only",
]


class PriceRangeEvaluationError(ValueError):
    """Raised when the price evaluation request cannot be resolved safely."""


def _absolute_dataset_path(repo_root: Path | None = None, dataset_path: Path | None = None) -> Path:
    root = (repo_root or REPO_ROOT).resolve()
    path = dataset_path or PRICE_RANGES_PATH
    return path if path.is_absolute() else root / path


def load_price_ranges(
    repo_root: Path | None = None,
    dataset_path: Path | None = None,
) -> pd.DataFrame:
    """Load and validate the Phase 7 MVP price ranges dataset."""
    path = _absolute_dataset_path(repo_root=repo_root, dataset_path=dataset_path)
    if not path.is_file():
        raise PriceRangeEvaluationError(f"Dataset no encontrado: {path}")

    df = pd.read_parquet(path)
    if df.empty:
        raise PriceRangeEvaluationError("El dataset de rangos de precio está vacío.")

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise PriceRangeEvaluationError(
            f"Faltan columnas requeridas en el dataset de rangos: {', '.join(sorted(missing))}"
        )

    normalized = df.copy()
    normalized["month"] = pd.to_numeric(normalized["month"], errors="coerce").astype("Int64")
    normalized["is_weekend"] = normalized["is_weekend"].astype(bool)
    return normalized


def _normalize_month(month: int | str) -> int:
    try:
        month_int = int(month)
    except (TypeError, ValueError) as exc:
        raise PriceRangeEvaluationError(f"Mes inválido: {month!r}") from exc
    if month_int < 1 or month_int > 12:
        raise PriceRangeEvaluationError(f"Mes inválido: {month_int}. Debe estar entre 1 y 12.")
    return month_int


def _normalize_day_type(day_type: str) -> tuple[str, bool]:
    normalized = str(day_type).strip().lower()
    if normalized not in ALLOWED_DAY_TYPES:
        raise PriceRangeEvaluationError(
            f"Tipo de día inválido: {day_type!r}. Usa 'weekday' o 'weekend'."
        )
    return normalized, ALLOWED_DAY_TYPES[normalized]


def _normalize_price(current_price_crc: float) -> float:
    try:
        price = float(current_price_crc)
    except (TypeError, ValueError) as exc:
        raise PriceRangeEvaluationError(f"Precio inválido: {current_price_crc!r}") from exc
    if price < 0:
        raise PriceRangeEvaluationError("El precio no puede ser negativo.")
    return price


def _validate_unit_id(unit_id: str) -> str:
    normalized = str(unit_id).strip()
    if normalized not in ALLOWED_UNIT_IDS:
        raise PriceRangeEvaluationError(
            f"Habitación inválida: {unit_id!r}. Usa uno de: {', '.join(sorted(ALLOWED_UNIT_IDS))}."
        )
    return normalized


def _build_warnings(segment: pd.Series) -> list[str]:
    warnings: list[str] = []
    if str(segment["confidence"]).strip().lower() == "baja":
        warnings.append("Datos insuficientes — no usar como referencia firme.")
    if bool(segment.get("usd_context_only", False)):
        warnings.append(
            "El baseline USD no supera al naive median en producción simulada. No se emite recomendación en USD."
        )
    return warnings


def _price_position(price: float, low: float, high: float) -> str:
    if price < low:
        return "por_debajo"
    if price > high:
        return "por_encima"
    return "dentro_del_rango"


def _build_message(
    *,
    room_label: str,
    month: int,
    day_type: str,
    current_price_crc: float,
    range_low_crc: float,
    range_high_crc: float,
    reference_price_crc: float,
    trend_label: str,
    confidence_label: str,
    n_reservations: int,
    price_position: str,
) -> str:
    if price_position == "por_debajo":
        position_text = "está por debajo del rango histórico"
    elif price_position == "por_encima":
        position_text = "está por encima del rango histórico"
    else:
        position_text = "está dentro del rango histórico"

    return (
        f"Para {room_label}, mes {month} y {day_type}, el rango histórico es "
        f"{range_low_crc:,.0f}–{range_high_crc:,.0f} CRC. "
        f"Tu precio actual de {current_price_crc:,.0f} CRC {position_text}. "
        f"Punto de referencia: {reference_price_crc:,.0f} CRC. "
        f"Tendencia esperada: {trend_label}. "
        f"Confianza: {confidence_label} (n={n_reservations} reservas en este segmento)."
    )


def evaluate_price(
    unit_id: str,
    month: int | str,
    day_type: str,
    current_price_crc: float,
    *,
    repo_root: Path | None = None,
    dataset_path: Path | None = None,
) -> dict:
    """Evaluate whether a CRC price sits below, within, or above the historical range."""
    normalized_unit_id = _validate_unit_id(unit_id)
    normalized_month = _normalize_month(month)
    normalized_day_type, is_weekend = _normalize_day_type(day_type)
    normalized_price = _normalize_price(current_price_crc)

    df = load_price_ranges(repo_root=repo_root, dataset_path=dataset_path)
    segment = df[
        (df["unit_id"] == normalized_unit_id)
        & (df["month"] == normalized_month)
        & (df["is_weekend"] == is_weekend)
    ]
    if segment.empty:
        raise PriceRangeEvaluationError(
            "No hay datos para el segmento solicitado. Resultado: sin_referencia_suficiente."
        )

    row = segment.iloc[0]
    range_low_crc = float(row["adr_p25_crc"])
    reference_price_crc = float(row["adr_median_crc"])
    range_high_crc = float(row["adr_p75_crc"])
    n_reservations = int(row["n_reservations"])
    warnings = _build_warnings(row)
    price_position = _price_position(normalized_price, range_low_crc, range_high_crc)

    result = {
        "unit_id": normalized_unit_id,
        "room_label": str(row["unit_display_name"]),
        "month": normalized_month,
        "day_type": normalized_day_type,
        "current_price_crc": normalized_price,
        "range_low_crc": range_low_crc,
        "range_high_crc": range_high_crc,
        "reference_price_crc": reference_price_crc,
        "trend_label": str(row["trend"]),
        "confidence_label": str(row["confidence"]),
        "confidence_reason": str(row["confidence_reason"]),
        "price_position": "sin_referencia_suficiente" if n_reservations < 1 else price_position,
        "message": _build_message(
            room_label=str(row["unit_display_name"]),
            month=normalized_month,
            day_type=normalized_day_type,
            current_price_crc=normalized_price,
            range_low_crc=range_low_crc,
            range_high_crc=range_high_crc,
            reference_price_crc=reference_price_crc,
            trend_label=str(row["trend"]),
            confidence_label=str(row["confidence"]),
            n_reservations=n_reservations,
            price_position=price_position,
        ),
        "warnings": warnings,
        "n_reservations": n_reservations,
        "uses_usd_context_only": bool(row["usd_context_only"]),
        "source_dataset": str(_absolute_dataset_path(repo_root=repo_root, dataset_path=dataset_path)),
    }

    lowered = result["message"].lower()
    for term in PROHIBITED_TERMS:
        if term in lowered:
            raise PriceRangeEvaluationError("El mensaje generado contiene lenguaje prohibido.")

    return result
