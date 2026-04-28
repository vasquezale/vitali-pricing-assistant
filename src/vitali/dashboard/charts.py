"""Plotly chart factories shared by the Streamlit app and the static HTML report."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PALETTE = {"CRC": "#2E86AB", "USD": "#A23B72"}
UNIT_COLORS = {"CieloRosa": "#E76F51", "Aqua": "#2A9D8F", "room_a": "#E76F51", "room_b": "#2A9D8F"}
AMARILLO_NOTE = (
    "⚠️ Gate Amarillo — datos de un solo alojamiento (2024–2026). "
    "Sin rentabilidad neta. Referencia orientativa, no sustituto del criterio humano."
)


def fig_monthly_income(trends: pd.DataFrame, currency: str) -> go.Figure:
    """Gross income by room over time for a given currency."""
    sub = trends[trends["currency"] == currency].copy()
    sub = sub.sort_values("month_start")
    fig = px.line(
        sub,
        x="month_start",
        y="gross_income_sum",
        color="unit_label",
        markers=True,
        color_discrete_map=UNIT_COLORS,
        labels={"month_start": "Mes", "gross_income_sum": f"Ingreso bruto ({currency})", "unit_label": "Habitación"},
        title=f"Ingreso bruto mensual por habitación — {currency}",
    )
    fig.update_layout(
        annotations=[dict(
            text=AMARILLO_NOTE, showarrow=False, xref="paper", yref="paper",
            x=0, y=-0.18, xanchor="left", font=dict(size=10, color="gray"),
        )],
        margin=dict(b=80),
        hovermode="x unified",
    )
    return fig


def fig_median_adr(trends: pd.DataFrame, currency: str) -> go.Figure:
    """Median gross ADR by room over time."""
    sub = trends[trends["currency"] == currency].copy()
    sub = sub.sort_values("month_start")
    fig = px.line(
        sub,
        x="month_start",
        y="median_gross_adr",
        color="unit_label",
        markers=True,
        color_discrete_map=UNIT_COLORS,
        labels={"month_start": "Mes", "median_gross_adr": f"ADR mediano ({currency})", "unit_label": "Habitación"},
        title=f"ADR bruto mediano por mes — {currency}",
    )
    fig.update_layout(
        annotations=[dict(
            text=AMARILLO_NOTE, showarrow=False, xref="paper", yref="paper",
            x=0, y=-0.18, xanchor="left", font=dict(size=10, color="gray"),
        )],
        margin=dict(b=80),
        hovermode="x unified",
    )
    return fig


def fig_reservations_heatmap(df: pd.DataFrame, currency: str) -> go.Figure:
    """Reservation count by month × unit."""
    sub = df[df["currency"] == currency].copy()
    pivot = (
        sub.groupby(["check_in_month", "unit_label"])
        .size()
        .reset_index(name="reservations")
        .pivot(index="unit_label", columns="check_in_month", values="reservations")
        .fillna(0)
    )
    pivot.columns = [f"M{c}" for c in pivot.columns]
    fig = px.imshow(
        pivot,
        text_auto=True,
        color_continuous_scale="Blues",
        labels=dict(x="Mes", y="Habitación", color="Reservas"),
        title=f"Distribución de reservas por mes — {currency}",
    )
    fig.update_layout(margin=dict(b=40))
    return fig


def fig_rolling_metrics(rolling: dict) -> go.Figure:
    """Rolling forward MAE per fold, split by currency."""
    rows = []
    for fold in rolling["folds"]:
        for cur_row in fold["by_currency"]:
            rows.append({
                "fold": fold["fold"],
                "currency": cur_row["currency"],
                "mae": cur_row["mae"],
                "mape_pct": cur_row["mape_pct"],
                "n": cur_row["n"],
                "mae_naive_median": cur_row["mae_naive_median"],
            })
    if not rows:
        return go.Figure()
    df_folds = pd.DataFrame(rows)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["MAE por fold (moneda nativa)", "MAPE % por fold"],
        shared_xaxes=False,
    )
    for cur, color in PALETTE.items():
        sub = df_folds[df_folds["currency"] == cur]
        if sub.empty:
            continue
        fig.add_trace(
            go.Bar(name=f"Baseline {cur}", x=sub["fold"], y=sub["mae"],
                   marker_color=color, legendgroup=cur, showlegend=True),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(name=f"Naive {cur}", x=sub["fold"], y=sub["mae_naive_median"],
                       mode="markers", marker=dict(symbol="x", size=12, color=color),
                       legendgroup=cur, showlegend=False),
            row=1, col=1,
        )
        fig.add_trace(
            go.Bar(name=f"MAPE {cur}", x=sub["fold"], y=sub["mape_pct"],
                   marker_color=color, legendgroup=cur, showlegend=False),
            row=1, col=2,
        )
    fig.update_layout(
        title="Rolling forward backtesting — Fase 6 (DEC-002)",
        barmode="group",
        annotations=[dict(
            text=AMARILLO_NOTE, showarrow=False, xref="paper", yref="paper",
            x=0, y=-0.22, xanchor="left", font=dict(size=10, color="gray"),
        )],
        margin=dict(b=90),
    )
    return fig


def fig_pricing_reference(ref: dict) -> go.Figure:
    """Box-style reference chart for the pricing query tool."""
    hist = ref.get("historical", {})
    currency = ref["currency"]
    unit_label = ref["unit_label"]
    month_name = ref["month_name"]
    weekend_label = "fin de semana" if ref["is_weekend"] else "entre semana"

    fig = go.Figure()

    if hist:
        fig.add_trace(go.Box(
            q1=[hist["p25"]], median=[hist["median"]], q3=[hist["p75"]],
            lowerfence=[hist["min"]], upperfence=[hist["max"]],
            name="Distribución histórica",
            marker_color=UNIT_COLORS.get(ref["unit_id"], "#888"),
            boxmean=False,
            width=0.4,
        ))

    pred = ref.get("model_pred_adr")
    if ref["model_reliable"] and pred and not np.isnan(pred):
        fig.add_hline(
            y=pred,
            line_dash="dash",
            line_color="#E63946",
            annotation_text=f"Referencia modelo: {pred:,.0f} {currency}",
            annotation_position="top right",
        )

    reliability_note = (
        "Modelo CRC — referencia orientativa (MAPE ~10.7 %)"
        if ref["model_reliable"]
        else "⚠️ Predicción USD no confiable — se muestra solo distribución histórica"
    )
    fig.update_layout(
        title=f"Referencia de precio — {unit_label} | {month_name} | {weekend_label} | {currency}",
        yaxis_title=f"ADR bruto ({currency})",
        xaxis_title="",
        annotations=[
            dict(text=reliability_note, showarrow=False, xref="paper", yref="paper",
                 x=0, y=-0.15, xanchor="left", font=dict(size=11, color="gray")),
            dict(text=AMARILLO_NOTE, showarrow=False, xref="paper", yref="paper",
                 x=0, y=-0.24, xanchor="left", font=dict(size=10, color="gray")),
        ],
        margin=dict(b=100),
        showlegend=True,
    )
    return fig
