"""Streamlit pricing assistant dashboard — Vitali (gate Amarillo).

Uso:
    uv run streamlit run src/vitali/dashboard/app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from vitali.dashboard.charts import (
    fig_median_adr,
    fig_monthly_income,
    fig_pricing_reference,
    fig_reservations_heatmap,
    fig_rolling_metrics,
)
from vitali.dashboard.data import (
    MONTH_NAMES,
    UNIT_LABELS,
    fit_baseline_all_data,
    load_monthly_trends,
    load_phase5_metrics,
    load_reservations,
    load_rolling_metrics,
    pricing_reference,
)

ROOT = Path(__file__).resolve().parents[3]

st.set_page_config(
    page_title="Vitali — Pricing Assistant",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def _load_data():
    df = load_reservations(ROOT)
    trends = load_monthly_trends(ROOT)
    rolling = load_rolling_metrics(ROOT)
    f5 = load_phase5_metrics(ROOT)
    return df, trends, rolling, f5


@st.cache_resource(show_spinner=False)
def _load_model():
    df = load_reservations(ROOT)
    return fit_baseline_all_data(df)


df, trends, rolling, f5 = _load_data()
model = _load_model()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Vitali")
    st.caption("Pricing Assistant — Decision Support")
    st.divider()
    st.warning(
        "**Gate Amarillo**\n\n"
        "Análisis basado en datos de un solo alojamiento (2024–2026). "
        "Sin rentabilidad neta. Referencia orientativa — no sustituye el criterio del operador."
    )
    st.divider()
    section = st.radio(
        "Sección",
        ["Tendencia de ingresos", "ADR por habitación", "Consulta de precio", "Evaluación del modelo", "Limitaciones"],
    )

# ── Header ────────────────────────────────────────────────────────────────────
st.title("Vitali — Pricing Assistant")
st.caption("Apoyo a decisiones de pricing | Airbnb Cartago, Costa Rica | Gate Amarillo")
st.divider()

# ── Tendencia de ingresos ─────────────────────────────────────────────────────
if section == "Tendencia de ingresos":
    st.header("Tendencia de ingresos")
    st.markdown(
        "Ingreso bruto mensual por habitación. **CRC y USD se muestran por separado** — "
        "no comparar valores numéricos entre monedas."
    )
    col1, col2 = st.columns(2)
    with col1:
        currency_sel = st.selectbox("Moneda", ["CRC", "USD"], key="income_cur")
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(fig_monthly_income(trends, currency_sel), use_container_width=True)
    with col_b:
        st.plotly_chart(fig_reservations_heatmap(df, currency_sel), use_container_width=True)

    total_res = len(df)
    crc_n = int((df["currency"] == "CRC").sum())
    usd_n = int((df["currency"] == "USD").sum())
    st.markdown(f"**Resumen:** {total_res} reservas totales — CRC: {crc_n} | USD: {usd_n}")

# ── ADR por habitación ────────────────────────────────────────────────────────
elif section == "ADR por habitación":
    st.header("ADR mediano por habitación")
    st.markdown(
        "Average Daily Rate (ADR) bruto mediano por mes. "
        "Meses con pocas reservas pueden mostrar valores atípicos — ver n de reservas."
    )
    cur_adr = st.selectbox("Moneda", ["CRC", "USD"], key="adr_cur")
    st.plotly_chart(fig_median_adr(trends, cur_adr), use_container_width=True)

    with st.expander("Tabla de datos"):
        sub = trends[trends["currency"] == cur_adr][
            ["month_label", "unit_label", "reservations", "median_gross_adr", "median_booking_lead_days"]
        ].rename(columns={
            "month_label": "Mes", "unit_label": "Habitación",
            "reservations": "Reservas", "median_gross_adr": f"ADR mediano ({cur_adr})",
            "median_booking_lead_days": "Lead días mediano",
        })
        st.dataframe(sub.sort_values(["Mes", "Habitación"]), use_container_width=True, hide_index=True)

# ── Consulta de precio ────────────────────────────────────────────────────────
elif section == "Consulta de precio":
    st.header("Consulta de precio de referencia")
    st.markdown(
        "Selecciona habitación, mes y tipo de noche para ver el rango histórico y, "
        "para CRC, la referencia del modelo."
    )
    st.info(
        "**CRC**: el modelo heurístico ofrece una referencia orientativa (MAPE ~10.7 %).\n\n"
        "**USD**: el modelo no supera la naive median en rolling forward — se muestra solo "
        "la distribución histórica como contexto.",
        icon="ℹ️",
    )
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        unit_sel = st.selectbox("Habitación", list(UNIT_LABELS.keys()),
                                format_func=lambda x: UNIT_LABELS[x])
    with col2:
        month_sel = st.selectbox("Mes (check-in)", list(MONTH_NAMES.keys()),
                                 format_func=lambda x: MONTH_NAMES[x])
    with col3:
        weekend_sel = st.selectbox("Tipo de noche", [0, 1],
                                   format_func=lambda x: "Fin de semana" if x else "Entre semana")
    with col4:
        currency_ref = st.selectbox("Moneda", ["CRC", "USD"], key="ref_cur")

    ref = pricing_reference(
        model, df,
        unit_id=unit_sel,
        month=month_sel,
        is_weekend=weekend_sel,
        currency=currency_ref,
    )

    if not ref["historical"]:
        st.warning(
            f"Sin datos históricos para esta combinación "
            f"({UNIT_LABELS[unit_sel]}, {MONTH_NAMES[month_sel]}, {currency_ref}). "
            "Prueba otra selección."
        )
    else:
        hist = ref["historical"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("P25 histórico", f"{hist['p25']:,.0f} {currency_ref}")
        m2.metric("Mediana histórica", f"{hist['median']:,.0f} {currency_ref}")
        m3.metric("P75 histórico", f"{hist['p75']:,.0f} {currency_ref}")
        m4.metric("n histórico", hist["n"])

        if ref["model_reliable"] and ref["model_pred_adr"] and not str(ref["model_pred_adr"]) == "nan":
            st.metric("Referencia modelo (CRC)", f"{ref['model_pred_adr']:,.0f} CRC")

        st.plotly_chart(fig_pricing_reference(ref), use_container_width=True)
        st.caption(
            "La referencia del modelo es resultado de medianas históricas por segmento. "
            "Meses o unidades con pocos datos pueden producir estimaciones poco robustas."
        )

# ── Evaluación del modelo ─────────────────────────────────────────────────────
elif section == "Evaluación del modelo":
    st.header("Evaluación del modelo — Rolling forward (Fase 6)")
    st.markdown(
        "Rolling forward expanding window: 4 folds, ventana test = 2 meses. "
        "Alineado con **DEC-002** (no split único). "
        "El marcador **×** indica la naive median en cada fold — si el baseline supera la × es útil."
    )
    st.plotly_chart(fig_rolling_metrics(rolling), use_container_width=True)

    st.subheader("Resumen por moneda")
    summary = rolling.get("summary_by_currency", {})
    for cur, vals in summary.items():
        with st.expander(f"**{cur}** — {vals['n_folds_with_data']} folds con datos"):
            c1, c2, c3 = st.columns(3)
            c1.metric("MAE medio", f"{vals['mae_mean']:,.1f}")
            c2.metric("MAE std", f"{vals['mae_std']:,.1f}")
            c3.metric("MAPE medio (%)", f"{vals['mape_pct_mean']:.1f} %")
            st.metric(
                "Mejora media vs. naive (%)",
                f"{vals['mae_improvement_vs_naive_pct_mean']:.1f} %",
                delta_color="normal" if vals['mae_improvement_vs_naive_pct_mean'] > 0 else "inverse",
                delta=f"{vals['mae_improvement_vs_naive_pct_mean']:.1f} %",
            )

    st.subheader("Residuos agregados")
    res_stats = rolling.get("residual_stats_by_currency", {})
    for cur, rs in res_stats.items():
        st.markdown(f"**{cur}** (n={rs['n_total']}): "
                    f"sesgo medio = {rs['mean_bias']:+,.1f} | std = {rs['std']:,.1f} | "
                    f"P25/P50/P75 = {rs['p25']:,.0f} / {rs['p50']:,.0f} / {rs['p75']:,.0f}")

    st.info(
        "**Hallazgo crítico:** El modelo USD es peor que la naive median en ambos folds rolling. "
        "El split único de Fase 5 reportó MAPE 7.5 % para USD — el rolling forward corrige "
        "esa estimación a ~18.9 %. Por eso las sugerencias USD no usan el modelo.",
        icon="⚠️",
    )

# ── Limitaciones ──────────────────────────────────────────────────────────────
elif section == "Limitaciones":
    st.header("Limitaciones y alcance (Gate Amarillo)")
    st.error(
        "Este sistema opera en **Gate Amarillo**. "
        "Las sugerencias son orientativas y no reemplazan el juicio del operador.",
        icon="🚨",
    )
    st.markdown("""
### Qué hace este sistema
- Muestra tendencias de ingreso bruto histórico por habitación y moneda.
- Provee un rango de referencia de ADR para combinaciones de habitación / mes / tipo de noche.
- Para CRC, el modelo heurístico mejora levemente la naive median (~9–10 %).
- Para USD, se muestra únicamente la distribución histórica (el modelo no es confiable en rolling).

### Qué NO hace este sistema
- **No calcula rentabilidad neta** — los ADR son brutos; comisiones y costos no están integrados.
- **No predice ocupación** futura.
- **No sustituye el criterio humano** de pricing — DEC-001.
- **No garantiza que el precio sugerido sea el óptimo** — no hay evidencia causal.

### Limitaciones de datos
- Un solo alojamiento desde mayo 2024 — generalización limitada.
- USD concentrado en segunda mitad del histórico — modelo USD inestable en rolling.
- Sin datos de competidores ni mercado externo.
- Sin reconciliación completa de costos (F2-03 abierto).

### Para habilitar la ruta verde
1. Reconciliar gastos operativos limpios (F2-03).
2. Integrar ingresos netos post-comisión de forma confiable.
3. Acumular más datos USD para estabilizar el modelo.
    """)
    st.caption(f"Última actualización de la evaluación: 2026-04-27 | Datos: {len(df)} reservas")
