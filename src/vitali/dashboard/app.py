"""Streamlit dashboard for the redesigned F7-MVP."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from vitali.dashboard.charts import (
    fig_median_adr,
    fig_monthly_balance,
    fig_monthly_income,
    fig_price_ranges_by_month,
    fig_projected_balance,
    fig_reservations_heatmap,
    fig_rolling_metrics,
)
from vitali.dashboard.data import (
    DISPLAY_CURRENCIES,
    FALLBACK_LABELS,
    MONTH_NAMES,
    UNIT_LABELS,
    balance_table_for_display,
    build_adr_history,
    build_balance_executive_insight,
    build_executive_summary,
    build_income_history,
    build_income_history_insights,
    build_price_executive_insight,
    build_projected_balance_insights,
    build_trends_insights,
    display_currency_note,
    format_currency_display,
    load_f7_monthly_balance,
    load_f7_projected_balances,
    load_f7_price_ranges,
    load_phase5_metrics,
    load_reservations,
    load_rolling_metrics,
    resolve_price_reference,
    translate_balance_quality_flag,
)
from vitali.mvp.monthly_balance import MonthlyBalanceError, evaluate_historical_balance


ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = {
    "conservative": "Conservador",
    "medium": "Medio",
    "wide": "Amplio",
}


st.set_page_config(
    page_title="Vitali — F7 MVP",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #F6EEDB 0%, #F4F1E6 100%);
            color: #223434;
        }
        .stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp div,
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stMarkdownContainer"] * {
            color: #223434;
        }
        [data-testid="stHeader"] {
            background: rgba(246, 238, 219, 0.88);
        }
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #F6EEDB 0%, #F4F1E6 100%);
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #E8F2EA 0%, #EAF5F7 100%);
            color: #284243;
        }
        section[data-testid="stSidebar"] * {
            color: #284243 !important;
        }
        .stSelectbox label, .stRadio label, .stNumberInput label {
            color: #334B4A !important;
            font-weight: 600;
        }
        .stSelectbox div[data-baseweb="select"] > div,
        .stNumberInput div[data-baseweb="input"] > div,
        .stNumberInput input {
            background: #FFF9ED !important;
            color: #223434 !important;
            border-color: #D5DECF !important;
        }
        .metric-card {
            background: #FFFDF8;
            border: 1px solid #DCE7D8;
            border-radius: 18px;
            padding: 18px 20px;
            min-height: 125px;
            box-shadow: 0 10px 24px rgba(96, 124, 110, 0.08);
        }
        .metric-label {
            font-size: 0.95rem;
            color: #5B6F68;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #234544;
            line-height: 1.15;
            word-break: break-word;
        }
        .metric-subvalue {
            font-size: 0.95rem;
            margin-top: 8px;
            color: #68807A;
        }
        .insight-box {
            background: #F4FBF5;
            border-left: 6px solid #6BAA75;
            border-radius: 14px;
            padding: 16px 18px;
            margin: 8px 0 14px 0;
            color: #244743;
        }
        .info-box {
            background: #EAF5FA;
            border-left: 6px solid #7AC7E3;
            border-radius: 14px;
            padding: 16px 18px;
            margin: 8px 0 14px 0;
            color: #204658;
        }
        .warning-box {
            background: #FFF6DA;
            border-left: 6px solid #E6C75A;
            border-radius: 14px;
            padding: 16px 18px;
            margin: 8px 0 14px 0;
            color: #5F4A05;
        }
        .soft-card {
            background: rgba(255, 253, 248, 0.78);
            border: 1px solid #DFE9E0;
            border-radius: 18px;
            padding: 18px 20px;
        }
        .section-note {
            font-size: 0.97rem;
            color: #4C6661;
        }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 1rem;
        }
        .stAlert, .stException {
            color: #5B2F28;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_metric_card(label: str, value: str, subvalue: str | None = None) -> None:
    sub_html = f'<div class="metric-subvalue">{subvalue}</div>' if subvalue else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_bullets(title: str, bullets: list[str], box_class: str = "insight-box") -> None:
    items = "".join(f"<li>{bullet}</li>" for bullet in bullets)
    st.markdown(
        f"""
        <div class="{box_class}">
            <strong>{title}</strong>
            <ul style="margin: 10px 0 0 18px;">
                {items}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _price_ranges_for_display(price_ranges: pd.DataFrame, display_currency: str) -> pd.DataFrame:
    frame = price_ranges.copy()
    divisor = 460.0 if display_currency == "USD" else 1.0
    frame["adr_p25_display"] = frame["adr_p25_crc"] / divisor
    frame["adr_median_display"] = frame["adr_median_crc"] / divisor
    frame["adr_p75_display"] = frame["adr_p75_crc"] / divisor
    return frame


def _balance_for_display(balance_df: pd.DataFrame, display_currency: str) -> pd.DataFrame:
    frame = balance_df.copy()
    divisor = 460.0 if display_currency == "USD" else 1.0
    value_column_map = {
        "ingresos_gross_crc": "gross_income_display",
        "expense_total_conservative": "expense_total_conservative_display",
        "expense_total_medium": "expense_total_medium_display",
        "expense_total_wide": "expense_total_wide_display",
        "balance_conservative": "balance_conservative_display",
        "balance_medium": "balance_medium_display",
        "balance_wide": "balance_wide_display",
    }
    for source_column, display_column in value_column_map.items():
        frame[display_column] = frame[source_column] / divisor
    return frame


def _projection_for_display(projection_df: pd.DataFrame, display_currency: str) -> pd.DataFrame:
    frame = projection_df.copy()
    divisor = 460.0 if display_currency == "USD" else 1.0
    for base in ["gross_income", "balance"]:
        for suffix in ["p25", "median", "p75"]:
            source = f"{base}_crc_{suffix}"
            if source in frame.columns:
                frame[f"{base}_display_{suffix}"] = frame[source] / divisor
    frame["estimated_expense_display"] = frame["estimated_expense_crc"] / divisor
    return frame


@st.cache_data(show_spinner=False)
def _load_data():
    reservations = load_reservations(ROOT)
    rolling = load_rolling_metrics(ROOT)
    phase5 = load_phase5_metrics(ROOT)
    price_ranges = load_f7_price_ranges(ROOT)
    monthly_balance = load_f7_monthly_balance(ROOT)
    return reservations, rolling, phase5, price_ranges, monthly_balance


reservations, rolling, phase5, price_ranges, monthly_balance = _load_data()
_inject_styles()

with st.sidebar:
    st.title("Vitali")
    st.caption("F7-MVP · Pricing + Balance mensual estimado")
    st.markdown(
        """
        <div class="warning-box">
            <strong>Gate Amarillo</strong><br>
            Sistema de apoyo a decisiones. No automatiza precios, no representa contabilidad formal y no sustituye el criterio del co-host.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="info-box">
            <strong>Moneda principal:</strong> CRC.<br>
            La vista USD usa una conversión fija temporal de 460 CRC/USD para facilitar la lectura.
        </div>
        """,
        unsafe_allow_html=True,
    )
    display_currency = st.radio(
        "Moneda de visualización",
        DISPLAY_CURRENCIES,
        format_func=lambda value: "CRC" if value == "CRC" else "USD (visual)",
    )
    section = st.radio(
        "Sección",
        [
            "Resumen ejecutivo",
            "Capa 1 · Precio",
            "Capa 2 · Balance",
            "Historia y tendencias",
            "Evaluación y advertencias",
        ],
    )


income_history = build_income_history(reservations, display_currency)
adr_history = build_adr_history(reservations, display_currency)
summary = build_executive_summary(reservations, monthly_balance, display_currency)
balance_display = _balance_for_display(monthly_balance, display_currency)

st.title("Vitali — Dashboard F7-MVP")
st.caption("Lectura operativa y ejecutiva para pricing e ingreso del negocio")
st.markdown(f"<div class='section-note'>{display_currency_note(display_currency)}</div>", unsafe_allow_html=True)
st.divider()

if section == "Resumen ejecutivo":
    st.subheader("Cómo leer esta app")
    _render_bullets(
        "Qué hace esta vista",
        [
            "Te muestra el comportamiento histórico del negocio con una sola lectura coherente hasta enero 2026.",
            "Los precios se leen primero como referencia operativa en CRC; si eliges USD, es solo una conversión visual temporal.",
            "El balance mensual estimado es orientativo y sirve como segunda opinión, no como estado financiero.",
        ],
        box_class="info-box",
    )

    row1, row2, row3, row4 = st.columns(4)
    with row1:
        _render_metric_card("ADR mediano", format_currency_display(summary["avg_adr_crc"], display_currency))
    with row2:
        _render_metric_card("Habitación más fuerte", summary["top_room_label"])
    with row3:
        _render_metric_card("Mes más fuerte", summary["top_month_label"])
    with row4:
        _render_metric_card("Reservas analizadas", f"{summary['reservation_count']}")

    if summary["latest_balance_month"] and summary["latest_balance_conservative_crc"] is not None:
        st.markdown(
            f"""
            <div class="info-box">
                <strong>Último mes operativo utilizable:</strong> {summary['latest_balance_month']}<br>
                Balance conservador estimado: {format_currency_display(summary['latest_balance_conservative_crc'], display_currency)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.plotly_chart(fig_monthly_income(income_history, display_currency), use_container_width=True)
    _render_bullets("Qué significa esta gráfica", build_income_history_insights(income_history))

    conservative_projection = _projection_for_display(load_f7_projected_balances(ROOT, "conservative"), display_currency)
    st.plotly_chart(fig_projected_balance(conservative_projection, display_currency), use_container_width=True)
    _render_bullets(
        "Qué significa esta proyección",
        build_projected_balance_insights(conservative_projection, display_currency),
        box_class="info-box",
    )

elif section == "Capa 1 · Precio":
    st.subheader("Capa 1 — Referencia operativa de precio")
    st.markdown(
        "<div class='section-note'>Primero te mostramos la referencia fija del contexto. Si quieres, luego puedes compararla con un precio manual.</div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        unit_id = st.selectbox("Habitación", list(UNIT_LABELS), format_func=lambda value: UNIT_LABELS[value])
    with col2:
        month = st.selectbox("Mes", list(MONTH_NAMES), format_func=lambda value: MONTH_NAMES[value])
    with col3:
        day_type = st.selectbox(
            "Tipo de día",
            ["weekday", "weekend"],
            format_func=lambda value: "Entre semana" if value == "weekday" else "Fin de semana",
        )

    reference = resolve_price_reference(reservations, unit_id=unit_id, month=month, day_type=day_type)
    insight = build_price_executive_insight(reference)
    display_price_ranges = _price_ranges_for_display(price_ranges, display_currency)

    row1, row2, row3, row4 = st.columns(4)
    with row1:
        _render_metric_card("Rango bajo", format_currency_display(reference["range_low_crc"], display_currency))
    with row2:
        _render_metric_card("Precio de referencia", format_currency_display(reference["reference_price_crc"], display_currency))
    with row3:
        _render_metric_card("Rango alto", format_currency_display(reference["range_high_crc"], display_currency))
    with row4:
        _render_metric_card("Tipo de referencia", reference["fallback_label"], f"{reference['n_reservations']} casos observados")

    st.markdown(
        f"""
        <div class="insight-box">
            <strong>{insight['headline']}</strong><br><br>
            <span>También equivale aproximadamente a {format_currency_display(reference['reference_price_crc'], 'USD')}.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_bullets("Qué significa este contexto", insight["bullets"])

    with st.expander("Comparar con mi precio actual (opcional)"):
        current_price = st.number_input("Precio manual en CRC", min_value=0.0, value=float(reference["reference_price_crc"]), step=1000.0)
        compare_insight = build_price_executive_insight(reference, current_price_crc=current_price)
        position_map = {
            "por_debajo": "Tu precio está por debajo del rango observado.",
            "dentro_del_rango": "Tu precio cae dentro del rango observado.",
            "por_encima": "Tu precio está por encima del rango observado.",
            None: "No hay comparación disponible.",
        }
        st.markdown(
            f"""
            <div class="info-box">
                <strong>{position_map[compare_insight['price_position']]}</strong><br>
                Precio ingresado: {format_currency_display(current_price, display_currency)} · equivalente: {format_currency_display(current_price, 'USD')}
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_bullets("Lectura de tu comparación", compare_insight["bullets"], box_class="info-box")

    st.plotly_chart(fig_price_ranges_by_month(display_price_ranges, unit_id, display_currency), use_container_width=True)
    if reference["uses_usd_context"]:
        st.markdown(
            """
            <div class="warning-box">
                Parte de este histórico reciente proviene de reservas originalmente en USD. Aquí lo mostramos convertido para sostener una sola lectura visual.
            </div>
            """,
            unsafe_allow_html=True,
        )

elif section == "Capa 2 · Balance":
    st.subheader("Capa 2 — Balance mensual estimado")
    st.markdown(
        "<div class='section-note'>Esta capa traduce ingreso bruto y gasto estimado a una lectura económica entendible. Sigue siendo orientativa.</div>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        scenario = st.selectbox("Escenario", list(SCENARIOS), format_func=lambda value: SCENARIOS[value])
    with col2:
        hist_year = st.selectbox("Año histórico", sorted(monthly_balance["year"].dropna().astype(int).unique().tolist()))
    with col3:
        available_months = (
            monthly_balance.loc[monthly_balance["year"].astype(int) == hist_year, "month"]
            .dropna()
            .astype(int)
            .sort_values()
            .unique()
            .tolist()
        )
        hist_month = st.selectbox("Mes histórico", available_months, format_func=lambda value: MONTH_NAMES[value])

    try:
        historical = evaluate_historical_balance(hist_year, hist_month, scenario, repo_root=ROOT)
    except MonthlyBalanceError as exc:
        st.markdown(
            f"""
            <div class="warning-box">
                <strong>No hay lectura histórica exacta para este corte.</strong><br>
                {exc}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        balance_insight = build_balance_executive_insight(historical)

        row1, row2, row3, row4 = st.columns(4)
        with row1:
            _render_metric_card("Ingreso bruto", format_currency_display(historical["gross_income_crc"], display_currency))
        with row2:
            _render_metric_card("Gasto estimado", format_currency_display(historical["expense_estimated_crc"], display_currency))
        with row3:
            _render_metric_card("Balance estimado", format_currency_display(historical["balance_estimated_crc"], display_currency))
        with row4:
            _render_metric_card("Calidad de lectura", translate_balance_quality_flag(historical["data_quality_flag"]))

        _render_bullets(balance_insight["headline"], balance_insight["bullets"])
        for warning in historical["warnings"]:
            box_class = "warning-box" if "remodelación" in warning or "incomplet" in warning.lower() else "info-box"
            st.markdown(f"<div class='{box_class}'>{warning}</div>", unsafe_allow_html=True)

    projected_balance = _projection_for_display(load_f7_projected_balances(ROOT, scenario=scenario), display_currency)
    st.plotly_chart(fig_projected_balance(projected_balance, display_currency), use_container_width=True)
    _render_bullets(
        "Qué significa esta proyección",
        build_projected_balance_insights(projected_balance, display_currency),
        box_class="info-box",
    )

    st.plotly_chart(fig_monthly_balance(balance_display, scenario, display_currency), use_container_width=True)
    _render_bullets(
        "Cómo leer el balance histórico",
        [
            "Las barras comparan ingreso bruto y gasto estimado del escenario elegido.",
            "La línea resume el colchón mensual aproximado después de ese gasto, no una utilidad neta oficial.",
            "Si un mes aparece incompleto o atípico, úsalo como contexto y no como referencia para reglas fijas.",
        ],
        box_class="info-box",
    )
    with st.expander("Ver tabla histórica"):
        st.dataframe(balance_table_for_display(monthly_balance, display_currency), use_container_width=True, hide_index=True)

elif section == "Historia y tendencias":
    st.subheader("Historia y tendencias")
    st.plotly_chart(fig_monthly_income(income_history, display_currency), use_container_width=True)
    _render_bullets("Qué significa esta gráfica", build_income_history_insights(income_history))

    st.plotly_chart(fig_median_adr(adr_history, display_currency), use_container_width=True)
    _render_bullets("Cómo leer el ADR", build_trends_insights(reservations), box_class="info-box")

    st.plotly_chart(fig_reservations_heatmap(reservations), use_container_width=True)
    _render_bullets(
        "Qué significa el mapa de reservas",
        [
            "Los cuadros más intensos muestran meses donde una habitación tuvo más movimiento.",
            "Más reservas no siempre significa mejor margen; también importa el precio promedio de ese tramo.",
            "Este mapa sirve para detectar concentración de demanda y meses flojos de un vistazo.",
        ],
        box_class="info-box",
    )

elif section == "Evaluación y advertencias":
    st.subheader("Evaluación y advertencias")
    st.plotly_chart(fig_rolling_metrics(rolling), use_container_width=True)
    _render_bullets(
        "Qué significa esta evaluación",
        [
            "El baseline en CRC funciona como referencia operativa razonable para el MVP.",
            "USD no se usa como recomendación principal; aquí sirve más como contexto histórico.",
            "La lógica del producto sigue siendo de apoyo a decisiones y no de automatización de precios.",
        ]
    )
    st.markdown(
        f"""
        <div class="warning-box">
            <strong>Referencia técnica actual:</strong><br>
            Baseline Fase 5 con `n_train={phase5['n_train']}` y `n_val={phase5['n_val']}`.<br>
            Todo lo que ves aquí debe leerse como señal orientativa, no como certeza financiera o comercial.
        </div>
        """,
        unsafe_allow_html=True,
    )
