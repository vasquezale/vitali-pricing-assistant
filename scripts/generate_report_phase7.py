"""Phase 7 — Generador de reporte HTML estático (gate Amarillo).

Produce un archivo HTML autocontenido con gráficas Plotly embebidas.

Uso:
    uv run python scripts/generate_report_phase7.py
    uv run python scripts/generate_report_phase7.py --out artifacts/reports/report_phase7.html
"""

from __future__ import annotations

import argparse
import textwrap
from datetime import date
from pathlib import Path

import plotly.io as pio

from vitali.dashboard.charts import (
    fig_median_adr,
    fig_monthly_income,
    fig_reservations_heatmap,
    fig_rolling_metrics,
)
from vitali.dashboard.data import (
    fit_baseline_all_data,
    load_monthly_trends,
    load_phase5_metrics,
    load_reservations,
    load_rolling_metrics,
    pricing_reference,
)
from vitali.dashboard.charts import fig_pricing_reference

ROOT = Path(__file__).resolve().parents[1]


def chart_html(fig, full_html: bool = False) -> str:
    return pio.to_html(fig, full_html=full_html, include_plotlyjs="cdn" if full_html else False)


def _section(title: str, body: str) -> str:
    return f"""
<section>
  <h2>{title}</h2>
  {body}
</section>
<hr>
"""


def build_html(df, trends, rolling, f5, model, out_path: Path) -> None:
    today = date.today().isoformat()
    n_res = len(df)

    # Charts
    fig_crc_income = fig_monthly_income(trends, "CRC")
    fig_usd_income = fig_monthly_income(trends, "USD")
    fig_crc_adr = fig_median_adr(trends, "CRC")
    fig_usd_adr = fig_median_adr(trends, "USD")
    fig_crc_heat = fig_reservations_heatmap(df, "CRC")
    fig_usd_heat = fig_reservations_heatmap(df, "USD")
    fig_rolling = fig_rolling_metrics(rolling)

    # Pricing reference examples: 4 representative segments
    ref_examples = [
        pricing_reference(model, df, unit_id="room_a", month=4, is_weekend=0, currency="CRC"),
        pricing_reference(model, df, unit_id="room_a", month=12, is_weekend=1, currency="CRC"),
        pricing_reference(model, df, unit_id="room_b", month=7, is_weekend=0, currency="CRC"),
        pricing_reference(model, df, unit_id="room_a", month=12, is_weekend=1, currency="USD"),
    ]
    ref_charts_html = "\n".join(
        f"<div style='margin-bottom:24px'>{chart_html(fig_pricing_reference(r))}</div>"
        for r in ref_examples
    )

    # Residual stats table
    res_stats = rolling.get("residual_stats_by_currency", {})
    res_rows = "".join(
        f"<tr><td>{cur}</td><td>{rs['n_total']}</td>"
        f"<td>{rs['mean_bias']:+,.1f}</td><td>{rs['std']:,.1f}</td>"
        f"<td>{rs['p25']:,.0f}</td><td>{rs['p50']:,.0f}</td><td>{rs['p75']:,.0f}</td></tr>"
        for cur, rs in res_stats.items()
    )

    # Summary table
    summary = rolling.get("summary_by_currency", {})
    sum_rows = "".join(
        f"<tr><td>{cur}</td><td>{v['n_folds_with_data']}</td>"
        f"<td>{v['mae_mean']:,.1f} ± {v['mae_std']:,.1f}</td>"
        f"<td>{v['mape_pct_mean']:.1f} ± {v['mape_pct_std']:.1f}</td>"
        f"<td>{v['mae_improvement_vs_naive_pct_mean']:+.1f} %</td></tr>"
        for cur, v in summary.items()
    )

    include_js = pio.to_html(fig_crc_income, full_html=False, include_plotlyjs="cdn")
    # First chart embeds cdn, rest just the div
    charts_crc_income = chart_html(fig_crc_income)
    charts_usd_income = chart_html(fig_usd_income)
    charts_crc_adr = chart_html(fig_crc_adr)
    charts_usd_adr = chart_html(fig_usd_adr)
    charts_crc_heat = chart_html(fig_crc_heat)
    charts_usd_heat = chart_html(fig_usd_heat)
    charts_rolling = chart_html(fig_rolling)

    html = textwrap.dedent(f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Vitali — Informe Ejecutivo Pricing Assistant</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 1100px; margin: 0 auto; padding: 32px 24px; color: #1a1a1a; }}
    h1 {{ font-size: 2rem; margin-bottom: 4px; }}
    h2 {{ font-size: 1.3rem; margin-top: 40px; color: #2a2a2a; border-left: 4px solid #E76F51;
          padding-left: 10px; }}
    .gate-banner {{ background: #fff8e1; border: 2px solid #f9a825; border-radius: 8px;
                    padding: 14px 20px; margin: 16px 0 32px; }}
    .gate-banner strong {{ color: #e65100; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 0.9rem; }}
    th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
    th {{ background: #f5f5f5; font-weight: 600; }}
    tr:nth-child(even) {{ background: #fafafa; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .note {{ font-size: 0.85rem; color: #666; margin-top: 8px; }}
    hr {{ border: none; border-top: 1px solid #e0e0e0; margin: 36px 0; }}
    footer {{ font-size: 0.8rem; color: #999; margin-top: 48px; }}
    .warning {{ background: #fdecea; border-left: 4px solid #e53935;
                padding: 10px 16px; border-radius: 4px; margin: 12px 0; }}
  </style>
</head>
<body>

<h1>Vitali — Informe Ejecutivo</h1>
<p>Pricing Assistant / Decision Support System | Airbnb Cartago, Costa Rica</p>
<p class="note">Generado: {today} | Reservas analizadas: {n_res} | Rango: Mayo 2024 – Enero 2026</p>

<div class="gate-banner">
  <strong>⚠️ Gate Amarillo</strong> — Este informe describe comportamiento histórico de ingresos
  y provee referencias de precio orientativas. <strong>No contiene cálculos de rentabilidad neta.</strong>
  Las sugerencias no reemplazan el criterio del operador (DEC-001). Datos de un solo alojamiento
  desde 2024 — generalización limitada.
</div>

{_section("1. Tendencia de ingresos brutos", f'''
<p>Ingreso bruto mensual por habitación. CRC y USD separados — no comparar valores entre monedas.</p>
<div class="two-col">
  <div>{charts_crc_income}</div>
  <div>{charts_usd_income}</div>
</div>
<div class="two-col">
  <div>{charts_crc_heat}</div>
  <div>{charts_usd_heat}</div>
</div>
''')}

{_section("2. ADR mediano por habitación", f'''
<p>Average Daily Rate (ADR) bruto mediano mensual. Meses con pocas reservas pueden mostrar variación alta.</p>
<div class="two-col">
  <div>{charts_crc_adr}</div>
  <div>{charts_usd_adr}</div>
</div>
''')}

{_section("3. Referencia de precio por segmento", f'''
<p>Ejemplos representativos: rango histórico + referencia modelo (solo CRC).</p>
<div class="warning">
  <strong>USD:</strong> el modelo heurístico no supera la naive median en rolling forward.
  Para USD se muestra únicamente la distribución histórica como contexto de mercado observado.
</div>
{ref_charts_html}
<p class="note">La línea roja punteada indica la referencia del modelo CRC (mediana jerárquica de ADR).
No es un precio óptimo — es un punto de anclaje basado en histórico del mismo segmento.</p>
''')}

{_section("4. Evaluación del modelo — Rolling forward (Fase 6 / DEC-002)", f'''
<p>4 folds expanding-window, ventana test = 2 meses. El marcador × indica la naive median por fold.</p>
{charts_rolling}
<h3>Resumen de métricas por moneda</h3>
<table>
  <tr><th>Moneda</th><th>Folds</th><th>MAE (media ± std)</th>
      <th>MAPE % (media ± std)</th><th>Mejora vs. naive</th></tr>
  {sum_rows}
</table>
<h3>Residuos agregados</h3>
<table>
  <tr><th>Moneda</th><th>n</th><th>Sesgo medio</th><th>Std</th>
      <th>P25</th><th>P50</th><th>P75</th></tr>
  {res_rows}
</table>
<div class="warning">
  <strong>Hallazgo clave:</strong> El modelo USD es peor que la naive median en ambos folds rolling
  (mejora media: −41 %). El split único de Fase 5 reportó MAPE 7.5 % para USD —
  el rolling forward corrige esa estimación a ~18.9 %. Esto valida DEC-002 (no usar split único).
</div>
''')}

{_section("5. Limitaciones y alcance", '''
<ul>
  <li><strong>Sin rentabilidad neta</strong> — ADR brutos sin descontar comisiones ni costos.</li>
  <li><strong>Un solo alojamiento</strong> (2 habitaciones) desde mayo 2024 — muestra reducida.</li>
  <li><strong>USD inestable</strong> — datos USD concentrados en segunda mitad del histórico.</li>
  <li><strong>Sin datos de competidores</strong> ni mercado externo.</li>
  <li><strong>Ruta verde bloqueada</strong> — requiere reconciliación de gastos operativos (F2-03).</li>
</ul>
<p>Para habilitar claims más fuertes: (1) limpiar taxonomía de gastos, (2) integrar ingresos netos
post-comisión, (3) acumular más datos USD.</p>
''')}

<footer>
  Proyecto Vitali · Fase 7 · Gate Amarillo · {today}<br>
  Evaluación: <code>artifacts/evaluation/phase6_rolling_metrics.json</code> |
  Script: <code>scripts/generate_report_phase7.py</code>
</footer>

</body>
</html>
""")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Reporte generado → {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera reporte HTML estático Fase 7.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "artifacts" / "reports" / "report_phase7.html",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    df = load_reservations(root)
    trends = load_monthly_trends(root)
    rolling = load_rolling_metrics(root)
    f5 = load_phase5_metrics(root)
    model = fit_baseline_all_data(df)

    build_html(df, trends, rolling, f5, model, args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
