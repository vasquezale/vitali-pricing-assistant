"""Phase 7 MVP monthly balance evaluator for the experimental executive layer."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
MONTHLY_BALANCE_PATH = Path("data/processed/f7_capa2_monthly_balance.parquet")
INCOME_PROJECTION_PATH = Path("artifacts/mvp/capa1_income_projection.json")
ALLOWED_SCENARIOS = {
    "conservative": "expense_total_conservative",
    "medium": "expense_total_medium",
    "wide": "expense_total_wide",
}
PROHIBITED_TERMS = (
    "utilidad neta",
    "rentabilidad garantizada",
    "p&l oficial",
    "estado financiero",
    "el negocio genera",
)
REQUIRED_BALANCE_COLUMNS = [
    "year",
    "month",
    "ingresos_gross_crc",
    "expense_negocio_crc",
    "expense_personal_crc",
    "expense_capex_crc",
    "expense_dudoso_crc",
    "expense_total_conservative",
    "expense_total_medium",
    "expense_total_wide",
    "balance_conservative",
    "balance_medium",
    "balance_wide",
    "is_renovation_month",
    "data_quality_flag",
    "expense_breakdown_available",
]


class MonthlyBalanceError(ValueError):
    """Raised when monthly balance guidance cannot be computed safely."""


def _absolute_path(repo_root: Path | None, relative_path: Path) -> Path:
    root = (repo_root or REPO_ROOT).resolve()
    return root / relative_path


def load_monthly_balance(
    repo_root: Path | None = None,
    dataset_path: Path | None = None,
) -> pd.DataFrame:
    """Load and validate the monthly balance dataset produced in 3A."""
    path = dataset_path or _absolute_path(repo_root, MONTHLY_BALANCE_PATH)
    if not path.is_absolute():
        path = _absolute_path(repo_root, path)
    if not path.is_file():
        raise MonthlyBalanceError(f"Dataset de balance no encontrado: {path}")

    df = pd.read_parquet(path)
    if df.empty:
        raise MonthlyBalanceError("El dataset de balance mensual está vacío.")

    missing = [column for column in REQUIRED_BALANCE_COLUMNS if column not in df.columns]
    if missing:
        raise MonthlyBalanceError(
            f"Faltan columnas requeridas en el dataset de balance: {', '.join(sorted(missing))}"
        )

    normalized = df.copy()
    for column in ["year", "month"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce").astype("Int64")

    numeric_columns = [
        "ingresos_gross_crc",
        "expense_negocio_crc",
        "expense_personal_crc",
        "expense_capex_crc",
        "expense_dudoso_crc",
        "expense_total_conservative",
        "expense_total_medium",
        "expense_total_wide",
        "balance_conservative",
        "balance_medium",
        "balance_wide",
    ]
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    return normalized


def load_income_projection(repo_root: Path | None = None, projection_path: Path | None = None) -> dict:
    """Load and validate the 3-month income projection JSON."""
    path = projection_path or _absolute_path(repo_root, INCOME_PROJECTION_PATH)
    if not path.is_absolute():
        path = _absolute_path(repo_root, path)
    if not path.is_file():
        raise MonthlyBalanceError(f"Proyección de ingresos no encontrada: {path}")

    projection = json.loads(path.read_text(encoding="utf-8"))
    projections = projection.get("projections")
    if not isinstance(projections, list) or not projections:
        raise MonthlyBalanceError("La proyección de ingresos no contiene meses proyectados.")
    return projection


def _validate_scenario(scenario: str) -> tuple[str, str]:
    normalized = str(scenario).strip().lower()
    if normalized not in ALLOWED_SCENARIOS:
        raise MonthlyBalanceError(
            f"Escenario inválido: {scenario!r}. Usa uno de: {', '.join(ALLOWED_SCENARIOS)}."
        )
    return normalized, ALLOWED_SCENARIOS[normalized]


def _validate_year(year: int | str) -> int:
    try:
        year_int = int(year)
    except (TypeError, ValueError) as exc:
        raise MonthlyBalanceError(f"Año inválido: {year!r}") from exc
    if year_int < 2000 or year_int > 2100:
        raise MonthlyBalanceError(f"Año inválido: {year_int}")
    return year_int


def _validate_month(month: int | str) -> int:
    try:
        month_int = int(month)
    except (TypeError, ValueError) as exc:
        raise MonthlyBalanceError(f"Mes inválido: {month!r}") from exc
    if month_int < 1 or month_int > 12:
        raise MonthlyBalanceError(f"Mes inválido: {month_int}. Debe estar entre 1 y 12.")
    return month_int


def _base_warnings() -> list[str]:
    return [
        "Este módulo es experimental y orientativo; no representa contabilidad formal.",
        "La lectura depende de la clasificación heurística entre gasto del negocio, personal, capex y dudoso.",
    ]


def _row_warnings(row: pd.Series) -> list[str]:
    warnings = _base_warnings()
    if str(row["data_quality_flag"]) == "incomplete_ocr":
        warnings.append(
            "Cobertura parcial de gastos: este mes no tiene desglose categorizado completo en el parquet interim."
        )
    if bool(row["is_renovation_month"]):
        warnings.append(
            "Mes atípico por remodelación: feb-mar 2026 no representa operación normal y debe excluirse de promedios operativos."
        )
    if not bool(row["expense_breakdown_available"]):
        warnings.append(
            "Para este mes conviene usar el egreso observado solo como contexto, no como referencia firme de balance."
        )
    return warnings


def _message_for_historical(
    *,
    year: int,
    month: int,
    scenario: str,
    income_crc: float,
    expense_crc: float,
    balance_crc: float,
) -> str:
    return (
        f"Para {year}-{month:02d}, el ingreso bruto histórico fue {income_crc:,.0f} CRC. "
        f"Bajo el escenario {scenario}, el gasto estimado es {expense_crc:,.0f} CRC y el balance mensual estimado es "
        f"{balance_crc:,.0f} CRC. Esta lectura es orientativa y se presenta antes de comisiones adicionales o revisión contable."
    )


def evaluate_historical_balance(
    year: int | str,
    month: int | str,
    scenario: str,
    *,
    repo_root: Path | None = None,
    dataset_path: Path | None = None,
) -> dict:
    """Return an orientative monthly balance view for a historical month."""
    normalized_year = _validate_year(year)
    normalized_month = _validate_month(month)
    normalized_scenario, expense_column = _validate_scenario(scenario)
    balance_column = expense_column.replace("expense_total_", "balance_")

    df = load_monthly_balance(repo_root=repo_root, dataset_path=dataset_path)
    segment = df[(df["year"] == normalized_year) & (df["month"] == normalized_month)]
    if segment.empty:
        raise MonthlyBalanceError("No hay datos para el mes solicitado.")

    row = segment.iloc[0]
    expense_value = row[expense_column]
    balance_value = row[balance_column]
    has_estimated_scenario = not pd.isna(expense_value) and not pd.isna(balance_value)

    if has_estimated_scenario:
        message = _message_for_historical(
            year=normalized_year,
            month=normalized_month,
            scenario=normalized_scenario,
            income_crc=float(row["ingresos_gross_crc"]),
            expense_crc=float(expense_value),
            balance_crc=float(balance_value),
        )
    else:
        message = (
            f"Para {normalized_year}-{normalized_month:02d}, existe ingreso bruto histórico de "
            f"{float(row['ingresos_gross_crc']):,.0f} CRC y egreso observado de {float(row['expense_observed_total_crc']):,.0f} CRC, "
            "pero no hay desglose suficiente para estimar el balance por escenario con confianza operativa."
        )

    lowered = message.lower()
    for term in PROHIBITED_TERMS:
        if term in lowered:
            raise MonthlyBalanceError("El mensaje generado contiene lenguaje prohibido.")

    return {
        "year": normalized_year,
        "month": normalized_month,
        "scenario": normalized_scenario,
        "income_type": "historical",
        "gross_income_crc": float(row["ingresos_gross_crc"]),
        "expense_estimated_crc": None if pd.isna(expense_value) else float(expense_value),
        "balance_estimated_crc": None if pd.isna(balance_value) else float(balance_value),
        "expense_observed_total_crc": float(row["expense_observed_total_crc"]),
        "expense_components": {
            "negocio": None if pd.isna(row["expense_negocio_crc"]) else float(row["expense_negocio_crc"]),
            "personal": None if pd.isna(row["expense_personal_crc"]) else float(row["expense_personal_crc"]),
            "capex": None if pd.isna(row["expense_capex_crc"]) else float(row["expense_capex_crc"]),
            "dudoso": None if pd.isna(row["expense_dudoso_crc"]) else float(row["expense_dudoso_crc"]),
        },
        "has_estimated_scenario": has_estimated_scenario,
        "data_quality_flag": str(row["data_quality_flag"]),
        "is_renovation_month": bool(row["is_renovation_month"]),
        "warnings": _row_warnings(row),
        "message": message,
        "source_dataset": str(dataset_path or _absolute_path(repo_root, MONTHLY_BALANCE_PATH)),
    }


def _operational_expense_baseline(df: pd.DataFrame) -> dict[str, float]:
    baseline_rows = df[
        df["expense_breakdown_available"]
        & (~df["is_renovation_month"])
        & (df["data_quality_flag"] == "ok")
    ].copy()
    if baseline_rows.empty:
        raise MonthlyBalanceError("No hay meses operativos suficientes para estimar gastos promedio.")

    baseline: dict[str, float] = {}
    for scenario, expense_column in ALLOWED_SCENARIOS.items():
        series = pd.to_numeric(baseline_rows[expense_column], errors="coerce").dropna()
        if series.empty:
            raise MonthlyBalanceError(f"No hay gasto estimado suficiente para el escenario {scenario}.")
        baseline[scenario] = float(series.mean())
    return baseline


def project_monthly_balance(
    scenario: str,
    *,
    repo_root: Path | None = None,
    dataset_path: Path | None = None,
    projection_path: Path | None = None,
) -> list[dict]:
    """Project the next 3 monthly balances using projected gross income and average operational expenses."""
    normalized_scenario, _expense_column = _validate_scenario(scenario)
    balance_df = load_monthly_balance(repo_root=repo_root, dataset_path=dataset_path)
    projection = load_income_projection(repo_root=repo_root, projection_path=projection_path)
    baseline_expenses = _operational_expense_baseline(balance_df)
    scenario_expense_crc = baseline_expenses[normalized_scenario]

    results: list[dict] = []
    for item in projection["projections"]:
        target_month = str(item["target_month"])
        income_p25 = item.get("gross_income_crc_p25")
        income_median = item.get("gross_income_crc_median")
        income_p75 = item.get("gross_income_crc_p75")

        result = {
            "target_month": target_month,
            "scenario": normalized_scenario,
            "income_type": "projected",
            "gross_income_crc_p25": income_p25,
            "gross_income_crc_median": income_median,
            "gross_income_crc_p75": income_p75,
            "estimated_expense_crc": scenario_expense_crc,
            "balance_crc_p25": None if income_p25 is None else float(income_p25) - scenario_expense_crc,
            "balance_crc_median": None if income_median is None else float(income_median) - scenario_expense_crc,
            "balance_crc_p75": None if income_p75 is None else float(income_p75) - scenario_expense_crc,
            "confidence_label": item.get("confidence", "baja"),
            "warnings": _base_warnings()
            + [
                "La proyección usa ingreso bruto histórico por mes calendario y gasto operativo promedio estimado.",
                "No representa P&L oficial ni utilidad neta garantizada.",
            ],
            "message": (
                f"Para {target_month}, bajo el escenario {normalized_scenario}, el gasto mensual estimado es "
                f"{scenario_expense_crc:,.0f} CRC. El balance mensual estimado cae en un rango orientativo de "
                f"{(float(income_p25) - scenario_expense_crc) if income_p25 is not None else float('nan'):,.0f} a "
                f"{(float(income_p75) - scenario_expense_crc) if income_p75 is not None else float('nan'):,.0f} CRC."
                if income_p25 is not None and income_p75 is not None
                else f"Para {target_month} no hay suficiente historial para proyectar el balance con este método."
            ),
            "income_reason": item.get("reason"),
        }
        lowered = result["message"].lower()
        for term in PROHIBITED_TERMS:
            if term in lowered:
                raise MonthlyBalanceError("La proyección generó lenguaje prohibido.")
        results.append(result)

    return results
