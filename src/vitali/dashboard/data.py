"""Data and presentation helpers shared by the F7 dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from vitali.mvp.monthly_balance import load_monthly_balance, project_monthly_balance
from vitali.mvp.price_ranges import load_price_ranges

_REPO_ROOT = Path(__file__).resolve().parents[3]

DISPLAY_FX_CRC_PER_USD = 460.0
DISPLAY_CURRENCIES = ("CRC", "USD")
UNIT_LABELS = {"room_a": "CieloRosa", "room_b": "Aqua"}
MONTH_NAMES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}
FALLBACK_LABELS = {
    "segment": "Referencia específica",
    "month": "Referencia aproximada del mes",
    "unit": "Referencia general de la habitación",
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
    df["month_start"] = df["check_in"].dt.to_period("M").dt.to_timestamp()
    df["month_label"] = df["month_start"].dt.strftime("%Y-%m")
    df["month_name"] = df["check_in_month"].map(MONTH_NAMES)
    df["display_date_label"] = df["month_start"].dt.strftime("%b %Y")
    return df


def load_monthly_trends(root: Path | None = None) -> pd.DataFrame:
    """Keep access to the original trends csv for compatibility and checks."""
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


def load_f7_price_ranges(root: Path | None = None) -> pd.DataFrame:
    return load_price_ranges(repo_root=root or _REPO_ROOT)


def load_f7_monthly_balance(root: Path | None = None) -> pd.DataFrame:
    return load_monthly_balance(repo_root=root or _REPO_ROOT)


def load_f7_projected_balances(root: Path | None = None, scenario: str = "conservative") -> pd.DataFrame:
    items = project_monthly_balance(scenario=scenario, repo_root=root or _REPO_ROOT)
    return pd.DataFrame(items)


def _convert_crc_value(value_crc: float | int | None, display_currency: str) -> float | None:
    if value_crc is None or pd.isna(value_crc):
        return None
    if display_currency == "USD":
        return float(value_crc) / DISPLAY_FX_CRC_PER_USD
    return float(value_crc)


def format_currency_display(
    value_crc: float | int | None,
    display_currency: str,
    *,
    decimals_crc: int = 0,
    decimals_usd: int = 1,
) -> str:
    value = _convert_crc_value(value_crc, display_currency)
    if value is None:
        return "N/D"
    if display_currency == "USD":
        return f"${value:,.{decimals_usd}f} USD"
    return f"{value:,.{decimals_crc}f} CRC"


def display_currency_note(display_currency: str) -> str:
    if display_currency == "USD":
        return "Conversión visual usando 460 CRC/USD. No representa tipo de cambio histórico real."
    return "Valores mostrados en CRC, usando el histórico normalizado completo."


def build_income_history(reservations: pd.DataFrame, display_currency: str) -> pd.DataFrame:
    history = (
        reservations.groupby(["month_start", "month_label", "unit_id", "unit_label"], dropna=False)
        .agg(
            gross_income_crc=("gross_income_crc", "sum"),
            reservations=("gross_income_crc", "size"),
            nights=("nights", "sum"),
        )
        .reset_index()
        .sort_values(["month_start", "unit_id"])
    )
    history["gross_income_display"] = history["gross_income_crc"].apply(
        lambda value: _convert_crc_value(value, display_currency)
    )
    history["display_currency"] = display_currency
    return history


def build_adr_history(reservations: pd.DataFrame, display_currency: str) -> pd.DataFrame:
    history = (
        reservations.groupby(["month_start", "month_label", "unit_id", "unit_label"], dropna=False)
        .agg(
            adr_crc=("gross_adr_crc", "median"),
            reservations=("gross_income_crc", "size"),
        )
        .reset_index()
        .sort_values(["month_start", "unit_id"])
    )
    history["adr_display"] = history["adr_crc"].apply(lambda value: _convert_crc_value(value, display_currency))
    history["display_currency"] = display_currency
    return history


def build_executive_summary(
    reservations: pd.DataFrame,
    monthly_balance: pd.DataFrame,
    display_currency: str,
) -> dict:
    income_history = build_income_history(reservations, display_currency="CRC")
    avg_adr_crc = float(reservations["gross_adr_crc"].median())
    top_room_row = (
        income_history.groupby("unit_label")["gross_income_crc"].sum().sort_values(ascending=False).index[0]
        if not income_history.empty
        else "N/D"
    )
    top_month_row = (
        income_history.groupby("month_label")["gross_income_crc"].sum().sort_values(ascending=False).index[0]
        if not income_history.empty
        else "N/D"
    )
    latest_balance_row = monthly_balance[monthly_balance["expense_breakdown_available"]].copy()
    latest_balance_month = (
        latest_balance_row.sort_values(["year", "month"]).iloc[-1] if not latest_balance_row.empty else None
    )
    return {
        "avg_adr_crc": avg_adr_crc,
        "avg_adr_display": _convert_crc_value(avg_adr_crc, display_currency),
        "top_room_label": top_room_row,
        "top_month_label": top_month_row,
        "reservation_count": int(len(reservations)),
        "latest_balance_month": None
        if latest_balance_month is None
        else f"{int(latest_balance_month['year'])}-{int(latest_balance_month['month']):02d}",
        "latest_balance_conservative_crc": None
        if latest_balance_month is None or pd.isna(latest_balance_month["balance_conservative"])
        else float(latest_balance_month["balance_conservative"]),
    }


def balance_table_for_display(balance_df: pd.DataFrame, display_currency: str) -> pd.DataFrame:
    table = balance_df.copy()
    table["period_label"] = table.apply(lambda row: f"{int(row['year'])}-{int(row['month']):02d}", axis=1)
    value_columns = [
        "ingresos_gross_crc",
        "expense_total_conservative",
        "expense_total_medium",
        "expense_total_wide",
        "balance_conservative",
        "balance_medium",
        "balance_wide",
    ]
    rename_map = {
        "ingresos_gross_crc": "Ingreso bruto",
        "expense_total_conservative": "Gasto conservador",
        "expense_total_medium": "Gasto medio",
        "expense_total_wide": "Gasto amplio",
        "balance_conservative": "Balance conservador",
        "balance_medium": "Balance medio",
        "balance_wide": "Balance amplio",
    }
    for column in value_columns:
        table[rename_map[column]] = table[column].apply(lambda value: format_currency_display(value, display_currency))
    table["Calidad"] = table["data_quality_flag"].map(
        {
            "ok": "Base operativa utilizable",
            "incomplete_ocr": "Gastos incompletos",
            "renovation_atypical": "Mes atípico por remodelación",
        }
    )
    table["Mes atípico"] = table["is_renovation_month"].map({True: "Sí", False: "No"})
    return table[
        [
            "period_label",
            "Ingreso bruto",
            "Gasto conservador",
            "Gasto medio",
            "Gasto amplio",
            "Balance conservador",
            "Balance medio",
            "Balance amplio",
            "Calidad",
            "Mes atípico",
        ]
    ].rename(columns={"period_label": "Período"})


def resolve_price_reference(
    reservations: pd.DataFrame,
    *,
    unit_id: str,
    month: int,
    day_type: str,
) -> dict:
    is_weekend = day_type == "weekend"
    base = reservations[reservations["unit_id"] == unit_id].copy()
    exact = base[(base["check_in_month"] == month) & (base["is_weekend"].astype(bool) == is_weekend)].copy()
    month_fallback = base[base["check_in_month"] == month].copy()
    unit_fallback = base.copy()

    if not exact.empty:
        segment = exact
        fallback_level = "segment"
    elif not month_fallback.empty:
        segment = month_fallback
        fallback_level = "month"
    elif not unit_fallback.empty:
        segment = unit_fallback
        fallback_level = "unit"
    else:
        raise ValueError("No hay datos suficientes para construir una referencia de precio.")

    reference_price_crc = float(segment["gross_adr_crc"].median())
    range_low_crc = float(segment["gross_adr_crc"].quantile(0.25))
    range_high_crc = float(segment["gross_adr_crc"].quantile(0.75))
    n_reservations = int(len(segment))

    month_all = base[base["check_in_month"] == month].copy()
    comparison_pool = month_all if not month_all.empty else unit_fallback
    weekend_pool = comparison_pool[comparison_pool["is_weekend"].astype(bool)]
    weekday_pool = comparison_pool[~comparison_pool["is_weekend"].astype(bool)]
    weekend_median = float(weekend_pool["gross_adr_crc"].median()) if not weekend_pool.empty else None
    weekday_median = float(weekday_pool["gross_adr_crc"].median()) if not weekday_pool.empty else None

    return {
        "unit_id": unit_id,
        "room_label": UNIT_LABELS[unit_id],
        "month": month,
        "month_name": MONTH_NAMES[month],
        "day_type": day_type,
        "range_low_crc": range_low_crc,
        "range_high_crc": range_high_crc,
        "reference_price_crc": reference_price_crc,
        "n_reservations": n_reservations,
        "fallback_level": fallback_level,
        "fallback_label": FALLBACK_LABELS[fallback_level],
        "uses_usd_context": bool((segment["currency"] == "USD").any()),
        "weekend_median_crc": weekend_median,
        "weekday_median_crc": weekday_median,
    }


def build_price_executive_insight(reference: dict, current_price_crc: float | None = None) -> dict:
    room_label = reference["room_label"]
    month_name = reference["month_name"]
    day_type_label = "fin de semana" if reference["day_type"] == "weekend" else "entre semana"

    support_sentence = (
        "Hay pocos casos observados en este tramo, así que úsalo como guía orientativa y no como regla firme."
        if reference["n_reservations"] < 5
        else "Este tramo ya tiene suficiente historial para usarlo como una referencia bastante útil."
    )

    if reference["fallback_level"] == "segment":
        scope_sentence = f"Esta lectura viene del mismo contexto: {room_label}, {month_name}, {day_type_label}."
    elif reference["fallback_level"] == "month":
        scope_sentence = (
            f"No había suficiente detalle para ese tipo de día, así que usamos una referencia más amplia del mes en {room_label}."
        )
    else:
        scope_sentence = (
            f"No había detalle suficiente para ese mes, así que usamos una referencia general de {room_label}."
        )

    weekend_sentence = None
    weekend_median = reference["weekend_median_crc"]
    weekday_median = reference["weekday_median_crc"]
    if weekend_median is not None and weekday_median is not None:
        diff = weekend_median - weekday_median
        if diff > 5000:
            weekend_sentence = f"En general, este cuarto soporta precios más altos en fin de semana por unos {diff:,.0f} CRC."
        elif diff < -5000:
            weekend_sentence = f"En este histórico, entre semana ha rendido mejor que fin de semana por unos {abs(diff):,.0f} CRC."
        else:
            weekend_sentence = "Entre semana y fin de semana se han comportado de forma bastante parecida en este tramo."

    price_position = None
    comparison_sentence = None
    if current_price_crc is not None:
        if current_price_crc < reference["range_low_crc"]:
            price_position = "por_debajo"
            comparison_sentence = "Tu precio actual está por debajo del rango observado para este contexto."
        elif current_price_crc > reference["range_high_crc"]:
            price_position = "por_encima"
            comparison_sentence = "Tu precio actual está por encima del rango observado para este contexto."
        else:
            price_position = "dentro_del_rango"
            comparison_sentence = "Tu precio actual cae dentro del rango que ya ha visto el negocio en este contexto."

    bullets = [scope_sentence, support_sentence]
    if weekend_sentence:
        bullets.append(weekend_sentence)
    if comparison_sentence:
        bullets.append(comparison_sentence)

    return {
        "headline": (
            f"Para {room_label} en {month_name}, el punto de referencia se mueve alrededor de "
            f"{reference['reference_price_crc']:,.0f} CRC."
        ),
        "bullets": bullets,
        "price_position": price_position,
    }


def build_balance_executive_insight(historical: dict) -> dict:
    if historical["has_estimated_scenario"] and historical["balance_estimated_crc"] is not None:
        balance = historical["balance_estimated_crc"]
        if balance < 0:
            headline = "Este mes luce apretado bajo este escenario."
        elif balance < historical["gross_income_crc"] * 0.15:
            headline = "Este mes deja margen, pero no demasiado."
        else:
            headline = "Este mes deja un colchón razonable bajo este escenario."
        bullets = [
            f"El ingreso bruto observado del mes fue {historical['gross_income_crc']:,.0f} CRC.",
            f"El gasto estimado para este escenario ronda {historical['expense_estimated_crc']:,.0f} CRC.",
            "Esta lectura es orientativa y no reemplaza una revisión contable.",
        ]
    else:
        headline = "Este mes no tiene suficiente base para estimar el balance por escenario con seguridad."
        bullets = [
            f"Sí existe ingreso bruto observado por {historical['gross_income_crc']:,.0f} CRC.",
            f"También hay egreso observado por {historical['expense_observed_total_crc']:,.0f} CRC.",
            "Lo que falta es suficiente desglose para convertirlo en una lectura operativa comparable.",
        ]
    return {"headline": headline, "bullets": bullets}


def build_income_history_insights(history_df: pd.DataFrame) -> list[str]:
    if history_df.empty:
        return ["No hay datos suficientes para describir el comportamiento de ingresos."]
    total_by_room = history_df.groupby("unit_label")["gross_income_crc"].sum().sort_values(ascending=False)
    top_room = total_by_room.index[0]
    top_month_row = history_df.groupby("month_label")["gross_income_crc"].sum().sort_values(ascending=False)
    top_month = top_month_row.index[0]
    latest_month = history_df["month_label"].max()
    latest_rows = history_df[history_df["month_label"] == latest_month].sort_values("gross_income_crc", ascending=False)
    latest_top_room = latest_rows.iloc[0]["unit_label"] if not latest_rows.empty else top_room
    insights = [
        f"{top_room} acumula el ingreso histórico más alto dentro del período visible.",
        f"El mes más fuerte del histórico fue {top_month}, medido sobre ingreso bruto ya normalizado a CRC.",
        f"En el último mes visible ({latest_month}), {latest_top_room} fue la habitación más fuerte.",
    ]
    if any(history_df["month_label"] >= "2025-09"):
        insights.append(
            "Desde septiembre 2025 parte del ingreso proviene de reservas originalmente en USD, aquí convertidas para mantener una sola lectura."
        )
    return insights


def build_trends_insights(reservations: pd.DataFrame) -> list[str]:
    room_summary = (
        reservations.groupby("unit_label")["gross_adr_crc"]
        .median()
        .sort_values(ascending=False)
        .reset_index()
    )
    weekend = reservations[reservations["is_weekend"].astype(bool)]["gross_adr_crc"].median()
    weekday = reservations[~reservations["is_weekend"].astype(bool)]["gross_adr_crc"].median()
    insights = [
        f"{room_summary.iloc[0]['unit_label']} suele sostener un ADR más alto que {room_summary.iloc[-1]['unit_label']} en el histórico observado.",
        "Un mes bajo no siempre implica menor precio; también puede reflejar menos reservas o menos noches vendidas.",
    ]
    if pd.notna(weekend) and pd.notna(weekday):
        if weekend > weekday:
            insights.append(
                f"En conjunto, los fines de semana suelen aceptar precios más altos que entre semana por unos {weekend - weekday:,.0f} CRC."
            )
        else:
            insights.append("En este histórico, la diferencia de precio entre semana y fin de semana es pequeña.")
    return insights


def build_projected_balance_insights(projection_df: pd.DataFrame, display_currency: str) -> list[str]:
    if projection_df.empty:
        return ["No hay suficiente historial para proyectar balances próximos."]
    best = projection_df.sort_values("balance_crc_median", ascending=False).iloc[0]
    worst = projection_df.sort_values("balance_crc_median", ascending=True).iloc[0]
    return [
        f"El mes proyectado con mejor margen es {best['target_month']}, con balance mediano de {format_currency_display(best['balance_crc_median'], display_currency)}.",
        f"El tramo más ajustado es {worst['target_month']}, así que conviene leerlo con más cautela.",
        "Estas proyecciones usan ingreso bruto histórico por mes calendario y gasto operativo promedio estimado.",
    ]


def translate_balance_quality_flag(flag: str) -> str:
    return {
        "ok": "Base operativa utilizable",
        "incomplete_ocr": "Gastos incompletos para este mes",
        "renovation_atypical": "Mes atípico por remodelación",
    }.get(flag, flag)
