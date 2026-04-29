from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts" / "mvp"
PROCESSED_DIR = ROOT / "data" / "processed"

UNIT_LABELS = {
    "room_a": "CieloRosa",
    "room_b": "Aqua",
}

PERSONAL_KEYWORDS = (
    "aliment",
    "supermerc",
    "pricesmart",
    "gasolina",
    "marchamo",
    "gym",
    "fitness",
    "vest",
    "ropa",
    "farm",
    "medic",
    "salud",
    "veterin",
    "mascota",
    "mosaico",
)
SHARED_KEYWORDS = (
    "agua",
    "luz",
    "internet",
    "starlink",
    "jasec",
    "jardin",
    "jard",
    "pool",
    "pozo",
    "basura",
    "seguridad",
)


@dataclass
class ArtifactInfo:
    name: str
    path: Path
    format: str
    proposed_use: str
    warnings: str


def ensure_dirs() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def human_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def classify_expense_detail(description: Any, bucket: Any) -> str:
    bucket_text = "" if pd.isna(bucket) else str(bucket).strip().lower()
    desc = "" if pd.isna(description) else str(description).strip().lower()

    if bucket_text == "operativo_defendible":
        return "negocio"
    if bucket_text == "posible_capex":
        return "capex"
    if any(keyword in desc for keyword in PERSONAL_KEYWORDS):
        return "personal"
    if any(keyword in desc for keyword in SHARED_KEYWORDS):
        return "compartido"
    return "dudoso"


def confidence_label(n: int) -> str:
    if n < 5:
        return "baja"
    if n <= 15:
        return "media"
    return "alta"


def confidence_reason(n: int) -> str:
    if n < 5:
        return f"Datos insuficientes — {n} reservas en el segmento"
    if n <= 15:
        return f"Soporte moderado — {n} reservas en el segmento"
    return f"Soporte alto — {n} reservas en el segmento"


def derive_trend(segment_median: float, unit_month_median: float) -> str:
    if pd.isna(segment_median) or pd.isna(unit_month_median) or unit_month_median == 0:
        return "estable"
    delta = (segment_median - unit_month_median) / unit_month_median
    if delta >= 0.05:
        return "alza"
    if delta <= -0.05:
        return "baja"
    return "estable"


def build_capa1_price_ranges() -> pd.DataFrame:
    df = pd.read_parquet(ROOT / "data" / "interim" / "income_reservations_fx_crc_interim.parquet").copy()
    df["unit_display_name"] = df["unit_id"].map(UNIT_LABELS).fillna(df["unit_id"])
    df["month"] = df["check_in_month"].astype(int)
    df["is_weekend"] = df["is_weekend"].astype(bool)
    df["gross_adr_crc"] = pd.to_numeric(df["gross_adr_crc"], errors="coerce")

    month_unit_medians = (
        df.groupby(["unit_id", "month"], dropna=False)["gross_adr_crc"]
        .median()
        .rename("unit_month_median_crc")
        .reset_index()
    )

    grouped = (
        df.groupby(["unit_id", "unit_display_name", "month", "is_weekend"], dropna=False)
        .agg(
            adr_p25_crc=("gross_adr_crc", lambda s: float(s.quantile(0.25))),
            adr_median_crc=("gross_adr_crc", "median"),
            adr_p75_crc=("gross_adr_crc", lambda s: float(s.quantile(0.75))),
            gross_income_crc=("gross_income_crc", "sum"),
            n_reservations=("gross_adr_crc", "size"),
            n_nights=("nights", "sum"),
            usd_observations=("currency", lambda s: int((s == "USD").sum())),
            crc_observations=("currency", lambda s: int((s == "CRC").sum())),
        )
        .reset_index()
    )

    grouped = grouped.merge(month_unit_medians, on=["unit_id", "month"], how="left")
    grouped["trend"] = grouped.apply(
        lambda row: derive_trend(row["adr_median_crc"], row["unit_month_median_crc"]),
        axis=1,
    )
    grouped["confidence"] = grouped["n_reservations"].apply(confidence_label)
    grouped["confidence_reason"] = grouped["n_reservations"].apply(confidence_reason)
    grouped["usd_context_only"] = grouped["usd_observations"] > 0
    grouped["segment_key"] = grouped.apply(
        lambda row: f"{row['unit_id']}|{int(row['month'])}|{'weekend' if row['is_weekend'] else 'weekday'}",
        axis=1,
    )
    grouped["data_sources"] = grouped.apply(
        lambda row: "mixed_currency_normalized_to_crc"
        if row["usd_observations"] and row["crc_observations"]
        else ("usd_normalized_to_crc" if row["usd_observations"] else "crc_native"),
        axis=1,
    )

    return grouped[
        [
            "segment_key",
            "unit_id",
            "unit_display_name",
            "month",
            "is_weekend",
            "adr_p25_crc",
            "adr_median_crc",
            "adr_p75_crc",
            "gross_income_crc",
            "n_reservations",
            "n_nights",
            "trend",
            "confidence",
            "confidence_reason",
            "usd_context_only",
            "usd_observations",
            "crc_observations",
            "data_sources",
        ]
    ].sort_values(["unit_id", "month", "is_weekend"]).reset_index(drop=True)


def build_capa2_balance() -> pd.DataFrame:
    reconcile = pd.read_parquet(ROOT / "data" / "interim" / "reconcile_monthly_indicative.parquet").copy()
    expenses = pd.read_parquet(ROOT / "data" / "interim" / "expenses_all_years_interim.parquet").copy()

    expenses["expense_detail_class"] = expenses.apply(
        lambda row: classify_expense_detail(row.get("descripcion"), row.get("expense_bucket")),
        axis=1,
    )

    expense_monthly = (
        expenses.groupby(["expense_year", "expense_month", "expense_detail_class"], dropna=False)["monto_crc"]
        .sum()
        .reset_index()
        .pivot(
            index=["expense_year", "expense_month"],
            columns="expense_detail_class",
            values="monto_crc",
        )
        .fillna(0.0)
        .reset_index()
    )
    expense_monthly.columns.name = None

    balance = reconcile.merge(
        expense_monthly,
        left_on=["year", "month"],
        right_on=["expense_year", "expense_month"],
        how="left",
    )

    for column in ["negocio", "personal", "compartido", "capex", "dudoso"]:
        if column not in balance.columns:
            balance[column] = 0.0
        balance[column] = pd.to_numeric(balance[column], errors="coerce")

    balance["is_renovation_month"] = (balance["year"] == 2026) & (balance["month"].isin([2, 3]))
    balance["expense_negocio_crc"] = balance["negocio"]
    balance["expense_personal_crc"] = balance["personal"]
    balance["expense_shared_crc"] = balance["compartido"]
    balance["expense_capex_crc"] = balance["capex"]
    balance["expense_dudoso_crc"] = balance["dudoso"]
    balance["expense_observed_total_crc"] = balance["egresos_crc"]

    has_categorized_breakdown = balance["expense_year"].notna()
    balance["expense_total_conservative"] = balance["expense_negocio_crc"].where(has_categorized_breakdown)
    balance["expense_total_medium"] = (
        balance["expense_negocio_crc"] + 0.5 * balance["expense_shared_crc"]
    ).where(has_categorized_breakdown)
    balance["expense_total_wide"] = (
        balance["expense_negocio_crc"] + balance["expense_shared_crc"] + balance["expense_personal_crc"]
    ).where(has_categorized_breakdown)

    balance["balance_conservative"] = (
        balance["ingresos_gross_crc"] - balance["expense_total_conservative"]
    )
    balance["balance_medium"] = balance["ingresos_gross_crc"] - balance["expense_total_medium"]
    balance["balance_wide"] = balance["ingresos_gross_crc"] - balance["expense_total_wide"]

    balance["data_quality_flag"] = "ok"
    balance.loc[~has_categorized_breakdown, "data_quality_flag"] = "incomplete_ocr"
    balance.loc[balance["is_renovation_month"], "data_quality_flag"] = "renovation_atypical"

    balance["expense_breakdown_available"] = has_categorized_breakdown
    balance["scenario_method"] = balance["expense_breakdown_available"].map(
        {
            True: "conservative=negocio; medium=negocio+50% compartido; wide=negocio+compartido+personal",
            False: "sin desglose categorizado en parquet interim; usar solo egresos observados del parquet de reconciliación",
        }
    )

    return balance[
        [
            "year",
            "month",
            "period",
            "ingresos_gross_crc",
            "ingresos_net_crc",
            "n_bookings",
            "expense_negocio_crc",
            "expense_personal_crc",
            "expense_shared_crc",
            "expense_capex_crc",
            "expense_dudoso_crc",
            "expense_observed_total_crc",
            "expense_total_conservative",
            "expense_total_medium",
            "expense_total_wide",
            "balance_conservative",
            "balance_medium",
            "balance_wide",
            "is_renovation_month",
            "data_quality_flag",
            "expense_breakdown_available",
            "scenario_method",
        ]
    ].sort_values(["year", "month"]).reset_index(drop=True)


def build_projection(capa1_df: pd.DataFrame) -> dict[str, Any]:
    income_df = pd.read_parquet(ROOT / "data" / "interim" / "income_reservations_fx_crc_interim.parquet").copy()
    latest_check_in = pd.to_datetime(income_df["check_in"]).max()
    next_month_starts = pd.date_range(latest_check_in.to_period("M").to_timestamp() + pd.offsets.MonthBegin(1), periods=3, freq="MS")

    monthly = (
        income_df.groupby(["check_in_year", "check_in_month"], dropna=False)
        .agg(
            gross_income_crc=("gross_income_crc", "sum"),
            n_reservations=("gross_income_crc", "size"),
        )
        .reset_index()
    )

    monthly["month"] = monthly["check_in_month"].astype(int)
    monthly_summary = (
        monthly.groupby("month")
        .agg(
            historical_gross_income_crc_p25=("gross_income_crc", lambda s: float(s.quantile(0.25))),
            historical_gross_income_crc_median=("gross_income_crc", "median"),
            historical_gross_income_crc_p75=("gross_income_crc", lambda s: float(s.quantile(0.75))),
            supporting_months=("gross_income_crc", "size"),
            supporting_reservations=("n_reservations", "sum"),
        )
        .reset_index()
    )

    projections = []
    for month_start in next_month_starts:
        month_num = int(month_start.month)
        row = monthly_summary.loc[monthly_summary["month"] == month_num]
        if row.empty:
            projections.append(
                {
                    "target_month": month_start.strftime("%Y-%m"),
                    "month": month_num,
                    "gross_income_crc_p25": None,
                    "gross_income_crc_median": None,
                    "gross_income_crc_p75": None,
                    "confidence": "baja",
                    "reason": "No hay suficiente historial mensual para este mes calendario.",
                }
            )
            continue
        rec = row.iloc[0]
        projections.append(
            {
                "target_month": month_start.strftime("%Y-%m"),
                "month": month_num,
                "gross_income_crc_p25": round(float(rec["historical_gross_income_crc_p25"]), 2),
                "gross_income_crc_median": round(float(rec["historical_gross_income_crc_median"]), 2),
                "gross_income_crc_p75": round(float(rec["historical_gross_income_crc_p75"]), 2),
                "confidence": confidence_label(int(rec["supporting_months"])),
                "reason": f"Basado en {int(rec['supporting_months'])} meses históricos y {int(rec['supporting_reservations'])} reservas agregadas para ese mes calendario.",
            }
        )

    return {
        "generated_from": str(ROOT / "data" / "interim" / "income_reservations_fx_crc_interim.parquet"),
        "latest_check_in_observed": latest_check_in.strftime("%Y-%m-%d"),
        "forecast_horizon_months": 3,
        "currency": "CRC",
        "method": "rango histórico mensual bruto en CRC por mes calendario (p25/mediana/p75), orientativo para F7-MVP",
        "projections": projections,
    }


def summarize_artifact(path: Path) -> tuple[str, str, list[str]]:
    if not path.exists():
        return ("no existe", "-", [])
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
        return (f"existe ({len(df)} filas)", human_size(path), [str(col) for col in df.columns])
    if path.suffix == ".csv":
        df = pd.read_csv(path)
        return (f"existe ({len(df)} filas)", human_size(path), [str(col) for col in df.columns])
    if path.suffix == ".json":
        data = load_json(path)
        if isinstance(data, dict):
            keys = list(data.keys())
            return ("existe", human_size(path), keys)
        if isinstance(data, list):
            keys = list(data[0].keys()) if data and isinstance(data[0], dict) else []
            return (f"existe ({len(data)} items)", human_size(path), keys)
    return ("existe", human_size(path), [])


def write_inventory_report(capa1_df: pd.DataFrame, capa2_df: pd.DataFrame, projection: dict[str, Any]) -> None:
    artifacts = [
        ArtifactInfo(
            name="Parquet interim ingresos/reservas",
            path=ROOT / "data/interim/income_reservations_fx_crc_interim.parquet",
            format="parquet",
            proposed_use="Base canónica de Capa 1 y de agregados de ingreso mensual.",
            warnings="Mezcla CRC y USD normalizados a CRC; usar `unit_id` como llave canónica y no confundirlo con nombre comercial sin evidencia adicional.",
        ),
        ArtifactInfo(
            name="Métricas baseline Fase 5",
            path=ROOT / "artifacts/baseline/phase5_metrics.json",
            format="json",
            proposed_use="Respaldar la legitimidad del baseline heurístico y la narrativa de CRC como fuente principal.",
            warnings="No contiene segmentos por habitación/mes; es evidencia de desempeño, no dataset transaccional.",
        ),
        ArtifactInfo(
            name="Métricas rolling Fase 6",
            path=ROOT / "artifacts/evaluation/phase6_rolling_metrics.json",
            format="json",
            proposed_use="Contexto de confianza y advertencias por moneda para F7.",
            warnings="La señal rolling está agregada por moneda, no por segmento habitación×mes×contexto.",
        ),
        ArtifactInfo(
            name="Income segment summary",
            path=ROOT / "artifacts/income_segment_summary.json",
            format="json",
            proposed_use="Validar cobertura por unidad, moneda, mes y contexto.",
            warnings="Está agregado por moneda original; no reemplaza el cálculo CRC integrado por segmento del MVP.",
        ),
        ArtifactInfo(
            name="Income segment insights",
            path=ROOT / "artifacts/income_segment_insights.json",
            format="json",
            proposed_use="Reutilizar mensajes de confianza y gaps descriptivos para UI/documentación.",
            warnings="Los insights están a nivel narrativo; no traen una tabla lista para join por segmento.",
        ),
        ArtifactInfo(
            name="Income trends tables",
            path=ROOT / "artifacts/income_trends/tables/monthly_income_trends.csv",
            format="csv",
            proposed_use="Apoyar tendencias y labels de habitación en visualizaciones futuras.",
            warnings="Son tablas agregadas auxiliares; no sustituyen el parquet interim ni cubren todos los joins necesarios.",
        ),
        ArtifactInfo(
            name="Tabla income FX",
            path=ROOT / "artifacts/income_analysis_table_fx.csv",
            format="csv",
            proposed_use="Referencia de columnas FX-normalizadas y validación de contrato upstream.",
            warnings="Útil como evidencia de schema; para F7 conviene consumir el parquet interim ya curado.",
        ),
        ArtifactInfo(
            name="Parquet interim gastos",
            path=ROOT / "data/interim/expenses_all_years_interim.parquet",
            format="parquet",
            proposed_use="Base de categorías de gasto y escenarios Capa 2.",
            warnings="Contiene solo 2025 pese a que `expense_profile.json` reporta 2026 Q1; `expense_bucket` sigue siendo heurístico.",
        ),
        ArtifactInfo(
            name="Parquet reconciliación mensual indicativa",
            path=ROOT / "data/interim/reconcile_monthly_indicative.parquet",
            format="parquet",
            proposed_use="Ingreso bruto mensual y egresos observados para balance mensual orientativo.",
            warnings="No es P&L formal; mezcla meses 2024 sin gastos y 2026 Q1 sin desglose categorizado.",
        ),
        ArtifactInfo(
            name="Perfil de gastos",
            path=ROOT / "artifacts/expense_profile.json",
            format="json",
            proposed_use="Validar cobertura temporal y advertencias de OCR/intake de gastos.",
            warnings="Es perfil agregado; no permite reconstruir categorías mensuales por sí solo.",
        ),
    ]

    lines = [
        "# Inventario de datos y dataset MVP integrado para F7-MVP",
        "",
        "## Resumen ejecutivo",
        "",
        "- Conclusión: sí existe base suficiente para continuar a Fase C/F7 sin reprocesar XLSX ni OCR desde cero.",
        "- Decisión operativa: Capa 1 debe construirse desde `data/interim/income_reservations_fx_crc_interim.parquet` en CRC normalizado, con apoyo de artifacts de tendencias y métricas.",
        "- Decisión operativa: Capa 2 debe partir de `data/interim/reconcile_monthly_indicative.parquet` y `data/interim/expenses_all_years_interim.parquet`, declarando que el desglose categorizado hoy solo cubre 2025.",
        "- Riesgo principal: el parquet interim de gastos no incluye 2026 Q1, aunque el perfil de gastos sí reporta esos meses; por eso los balances de 2026-01/02/03 quedan con bandera de calidad.",
        "",
        "## Tarea 1 — Inventario real de artifacts",
        "",
        "| Artifact | Ruta | Formato | Estado | Tamaño / filas | Columnas principales | Uso propuesto | Riesgos / advertencias |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for artifact in artifacts:
        status, size_or_rows, columns = summarize_artifact(artifact.path)
        rel = artifact.path.relative_to(ROOT)
        column_preview = ", ".join(columns[:8]) if columns else "-"
        lines.append(
            f"| {artifact.name} | `{rel}` | {artifact.format} | {status} | {size_or_rows} | {column_preview} | {artifact.proposed_use} | {artifact.warnings} |"
        )

    capa1_cols = ", ".join(capa1_df.columns.tolist())
    capa2_cols = ", ".join(capa2_df.columns.tolist())

    lines.extend(
        [
            "",
            "## Tarea 2 — Validación mínima de columnas",
            "",
            "### Capa 1",
            "",
            f"- Dataset principal validado: `data/interim/income_reservations_fx_crc_interim.parquet`.",
            f"- Columnas encontradas: {capa1_cols}.",
            "- Cobertura directa confirmada: `unit_id`, `check_in_month`, `is_weekend`, `gross_adr_crc`, `gross_income_crc`, `nights`, `currency`.",
            "- Columnas derivables: `confidence`, `confidence_reason`, `trend`, `usd_context_only`, `n_reservations`.",
            "- Columnas faltantes no bloqueantes: ocupación real/capacidad instalada por habitación, soporte rolling por segmento fino.",
            "- Observación: el artifact `income_segment_insights.json` sí incluye `confidence_label` y `confidence_reason`, pero no en formato tabular joinable por segmento; por eso se recalcula en el dataset derivado.",
            "",
            "### Capa 2",
            "",
            f"- Datasets principales validados: `data/interim/expenses_all_years_interim.parquet`, `data/interim/reconcile_monthly_indicative.parquet`.",
            f"- Columnas encontradas en salida integrada: {capa2_cols}.",
            "- Cobertura directa confirmada: `year`, `month`, `ingresos_gross_crc`, `egresos_crc`/`expense_observed_total_crc`, `expense_bucket`, `descripcion`.",
            "- Columnas derivables: separación `negocio/personal/compartido/capex/dudoso`, escenarios conservador/medio/amplio, `is_renovation_month`, `data_quality_flag`.",
            "- Columnas faltantes no bloqueantes: fuente OCR por transacción, clasificación contable formal, asignación por habitación, reconciliación payout/comisiones exacta.",
            "- Gap crítico documentado: el parquet interim de gastos hoy solo cubre 2025; los meses 2026-01/02/03 existen en `expense_profile.json` y en la reconciliación mensual, pero no con desglose categorizado en el parquet interim actual.",
            "",
            "## Tarea 3 — Outputs preparados",
            "",
            "| Output | Ruta | Descripción |",
            "|---|---|---|",
            "| Dataset Capa 1 | `data/processed/f7_capa1_price_ranges.parquet` | Segmentos por `unit_id × month × is_weekend` en CRC con rango histórico, tendencia y confianza. |",
            "| Dataset Capa 2 | `data/processed/f7_capa2_monthly_balance.parquet` | Balance mensual orientativo con escenarios y banderas de calidad. |",
            "| Proyección base | `artifacts/mvp/capa1_income_projection.json` | Rango histórico mensual bruto CRC para los próximos 3 meses calendario. |",
            "",
            "## Contratos de salida propuestos",
            "",
            "### Output 1 — `data/processed/f7_capa1_price_ranges.parquet`",
            "",
            "- Grano: una fila por `unit_id × month × is_weekend`.",
            "- Moneda operativa: CRC.",
            "- Fuente primaria: `income_reservations_fx_crc_interim.parquet`.",
            "- Advertencia contractual: `unit_display_name` reaprovecha el label visible en `artifacts/income_trends/tables/monthly_income_trends.csv`; `unit_id` sigue siendo la llave canónica.",
            "",
            "### Output 2 — `data/processed/f7_capa2_monthly_balance.parquet`",
            "",
            "- Grano: una fila por `year × month`.",
            "- Fuente primaria: `reconcile_monthly_indicative.parquet` + `expenses_all_years_interim.parquet`.",
            "- Regla de escenarios implementada:",
            "  - conservador = negocio",
            "  - medio = negocio + 50% compartido",
            "  - amplio = negocio + compartido + personal",
            "- Advertencia contractual: los escenarios solo se calculan donde existe desglose categorizado en el parquet interim; 2026 Q1 queda señalado como cobertura incompleta o atípica.",
            "",
            "### Output 3 — `artifacts/mvp/capa1_income_projection.json`",
            "",
            "- Horizonte: próximos 3 meses desde el último `check_in` observado.",
            "- Método: percentiles históricos de ingreso bruto mensual CRC por mes calendario.",
            "- Uso previsto: alimentar Prompt 3D con una proyección honesta y de baja complejidad.",
            "",
            "## Evidencia de generación",
            "",
            f"- Filas Capa 1 generadas: {len(capa1_df)}.",
            f"- Filas Capa 2 generadas: {len(capa2_df)}.",
            f"- Meses proyectados: {len(projection['projections'])}.",
        ]
    )

    (ARTIFACTS_DIR / "data_inventory_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ensure_dirs()
    capa1_df = build_capa1_price_ranges()
    capa2_df = build_capa2_balance()
    projection = build_projection(capa1_df)

    capa1_df.to_parquet(PROCESSED_DIR / "f7_capa1_price_ranges.parquet", index=False)
    capa2_df.to_parquet(PROCESSED_DIR / "f7_capa2_monthly_balance.parquet", index=False)
    (ARTIFACTS_DIR / "capa1_income_projection.json").write_text(
        json.dumps(projection, ensure_ascii=False, indent=2) + "\n"
    )
    write_inventory_report(capa1_df, capa2_df, projection)


if __name__ == "__main__":
    main()
