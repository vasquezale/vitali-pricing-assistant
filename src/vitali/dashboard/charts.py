"""Plotly chart factories for the redesigned F7 dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


PALETTE = {
    "verde": "#6BAA75",
    "celeste": "#7AC7E3",
    "amarillo": "#E6C75A",
    "azul": "#4F6D8A",
    "coral": "#E68A6B",
    "aqua": "#39AFA9",
    "rosa": "#D97C9A",
    "gris": "#6B7280",
}
UNIT_COLORS = {"CieloRosa": PALETTE["coral"], "Aqua": PALETTE["aqua"], "room_a": PALETTE["coral"], "room_b": PALETTE["aqua"]}
PLOT_TEMPLATE = "plotly_white"


def _base_layout(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template=PLOT_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F9F4E8",
        margin=dict(l=24, r=24, t=72, b=72),
        font=dict(color="#294040", size=13),
        legend_title_text="",
        title_font=dict(color="#203738", size=22),
        legend=dict(
            font=dict(color="#294040", size=14),
            bgcolor="rgba(249,244,232,0.85)",
            bordercolor="#D8E0D0",
            borderwidth=1,
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor="#D9E2D5",
        tickfont=dict(color="#415C5A"),
        title_font=dict(color="#294040", size=16),
    )
    fig.update_yaxes(
        gridcolor="#DCE7D8",
        zeroline=False,
        linecolor="#D9E2D5",
        tickfont=dict(color="#415C5A"),
        title_font=dict(color="#294040", size=16),
    )
    return fig


def fig_monthly_income(history_df: pd.DataFrame, display_currency: str) -> go.Figure:
    fig = px.line(
        history_df.sort_values("month_start"),
        x="month_start",
        y="gross_income_display",
        color="unit_label",
        markers=True,
        color_discrete_map=UNIT_COLORS,
        labels={"month_start": "Mes", "gross_income_display": f"Ingreso bruto ({display_currency})", "unit_label": "Habitación"},
        title=f"Ingreso bruto mensual por habitación — {display_currency}",
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8))
    fig.update_layout(hovermode="x unified")
    return _base_layout(fig)


def fig_median_adr(adr_df: pd.DataFrame, display_currency: str) -> go.Figure:
    fig = px.line(
        adr_df.sort_values("month_start"),
        x="month_start",
        y="adr_display",
        color="unit_label",
        markers=True,
        color_discrete_map=UNIT_COLORS,
        labels={"month_start": "Mes", "adr_display": f"ADR mediano ({display_currency})", "unit_label": "Habitación"},
        title=f"ADR mediano por habitación — {display_currency}",
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8))
    fig.update_layout(hovermode="x unified")
    return _base_layout(fig)


def fig_reservations_heatmap(reservations: pd.DataFrame) -> go.Figure:
    pivot = (
        reservations.groupby(["unit_label", "check_in_month"])
        .size()
        .reset_index(name="reservations")
        .pivot(index="unit_label", columns="check_in_month", values="reservations")
        .fillna(0)
    )
    fig = px.imshow(
        pivot,
        text_auto=True,
        color_continuous_scale=[
            [0.0, "#F5ECD7"],
            [0.5, "#A8DADC"],
            [1.0, "#4F9D8E"],
        ],
        labels=dict(x="Mes", y="Habitación", color="Reservas"),
        title="Reservas por mes y habitación",
    )
    return _base_layout(fig)


def fig_rolling_metrics(rolling: dict) -> go.Figure:
    rows = []
    for fold in rolling["folds"]:
        for cur_row in fold["by_currency"]:
            rows.append(
                {
                    "fold": fold["fold"],
                    "currency": cur_row["currency"],
                    "mae": cur_row["mae"],
                    "mape_pct": cur_row["mape_pct"],
                    "mae_naive_median": cur_row["mae_naive_median"],
                }
            )
    df_folds = pd.DataFrame(rows)
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=["MAE por fold", "MAPE por fold (%)"],
        horizontal_spacing=0.12,
    )
    currency_colors = {"CRC": PALETTE["azul"], "USD": PALETTE["rosa"]}
    for currency, color in currency_colors.items():
        sub = df_folds[df_folds["currency"] == currency]
        if sub.empty:
            continue
        fig.add_trace(go.Bar(name=f"Baseline {currency}", x=sub["fold"], y=sub["mae"], marker_color=color), row=1, col=1)
        fig.add_trace(
            go.Scatter(
                name=f"Naive {currency}",
                x=sub["fold"],
                y=sub["mae_naive_median"],
                mode="markers",
                marker=dict(symbol="x", size=11, color=color),
                showlegend=False,
            ),
            row=1,
            col=1,
        )
        fig.add_trace(go.Bar(name=f"MAPE {currency}", x=sub["fold"], y=sub["mape_pct"], marker_color=color, showlegend=False), row=1, col=2)
    fig.update_layout(title="Evaluación rolling forward del baseline")
    return _base_layout(fig)


def fig_price_ranges_by_month(price_ranges: pd.DataFrame, unit_id: str, display_currency: str) -> go.Figure:
    sub = price_ranges[price_ranges["unit_id"] == unit_id].copy()
    room_label = sub["unit_display_name"].iloc[0] if not sub.empty and "unit_display_name" in sub.columns else unit_id
    sub["day_type"] = sub["is_weekend"].map({True: "Fin de semana", False: "Entre semana"})
    for column in ["adr_p25_display", "adr_median_display", "adr_p75_display"]:
        if column not in sub.columns:
            raise ValueError(f"Falta columna de presentación: {column}")
    fig = go.Figure()
    for day_type, color in [("Entre semana", PALETTE["azul"]), ("Fin de semana", PALETTE["coral"])]:
        day_sub = sub[sub["day_type"] == day_type].sort_values("month")
        if day_sub.empty:
            continue
        fill_rgba = "rgba(79,109,138,0.16)" if day_type == "Entre semana" else "rgba(230,138,107,0.18)"
        fig.add_trace(go.Scatter(x=day_sub["month"], y=day_sub["adr_p75_display"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(
            go.Scatter(
                x=day_sub["month"],
                y=day_sub["adr_p25_display"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor=fill_rgba,
                name=f"Rango {day_type}",
                hovertemplate="Mes %{x}<br>Rango %{y:,.1f} " + display_currency + "<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=day_sub["month"],
                y=day_sub["adr_median_display"],
                mode="lines+markers",
                line=dict(color=color, width=3),
                marker=dict(size=8),
                name=f"Referencia {day_type}",
                hovertemplate="Mes %{x}<br>Referencia %{y:,.1f} " + display_currency + "<extra></extra>",
            )
        )
    fig.update_layout(
        title=f"Rango histórico mensual de {room_label}",
        xaxis_title="Mes",
        yaxis_title=f"Precio observado ({display_currency})",
        hovermode="x unified",
    )
    return _base_layout(fig)


def fig_monthly_balance(balance_df: pd.DataFrame, scenario: str, display_currency: str) -> go.Figure:
    scenario_key = scenario.lower()
    expense_col = f"expense_total_{scenario_key}_display"
    balance_col = f"balance_{scenario_key}_display"
    sub = balance_df.copy()
    sub["period_label"] = sub.apply(lambda row: f"{int(row['year'])}-{int(row['month']):02d}", axis=1)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=sub["period_label"], y=sub["gross_income_display"], name="Ingreso bruto", marker_color=PALETTE["aqua"]))
    fig.add_trace(go.Bar(x=sub["period_label"], y=sub[expense_col], name="Gasto estimado", marker_color=PALETTE["amarillo"]))
    fig.add_trace(
        go.Scatter(
            x=sub["period_label"],
            y=sub[balance_col],
            mode="lines+markers",
            name="Balance estimado",
            line=dict(color=PALETTE["verde"], width=3),
            marker=dict(size=8),
        )
    )
    fig.update_layout(
        title=f"Balance mensual estimado — escenario {scenario_key}",
        xaxis_title="Mes",
        yaxis_title=display_currency,
        barmode="group",
    )
    return _base_layout(fig)


def fig_projected_balance(projection_df: pd.DataFrame, display_currency: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=projection_df["target_month"],
            y=projection_df["gross_income_display_median"],
            name="Ingreso bruto proyectado",
            marker_color=PALETTE["celeste"],
        )
    )
    fig.add_trace(
        go.Scatter(
            x=projection_df["target_month"],
            y=projection_df["balance_display_median"],
            mode="lines+markers",
            name="Balance proyectado",
            line=dict(color=PALETTE["verde"], width=3),
            marker=dict(size=8),
            error_y=dict(
                type="data",
                symmetric=False,
                array=projection_df["balance_display_p75"] - projection_df["balance_display_median"],
                arrayminus=projection_df["balance_display_median"] - projection_df["balance_display_p25"],
            ),
        )
    )
    fig.update_layout(
        title="Próximos 3 meses — ingreso y balance proyectado",
        xaxis_title="Mes objetivo",
        yaxis_title=display_currency,
    )
    return _base_layout(fig)
