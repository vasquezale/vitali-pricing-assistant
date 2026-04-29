# Handoff — Capa 2 Monthly Balance

## Módulo creado

- Ruta: `src/vitali/mvp/monthly_balance.py`
- APIs principales:
  - `evaluate_historical_balance(year, month, scenario, ...) -> dict`
  - `project_monthly_balance(scenario, ...) -> list[dict]`
  - `load_monthly_balance(...) -> pandas.DataFrame`

## Datasets usados

- Fuente principal: `data/processed/f7_capa2_monthly_balance.parquet`
- Proyección de ingresos: `artifacts/mvp/capa1_income_projection.json`

## Escenarios soportados

- `conservative`
- `medium`
- `wide`

## Reglas implementadas

- Histórico:
  - usa `expense_total_<scenario>` y `balance_<scenario>` cuando existen
  - si no existe desglose suficiente, devuelve contexto histórico y warnings sin inventar balance por escenario
- Proyección:
  - usa la proyección de ingreso bruto de los próximos 3 meses
  - resta un gasto operativo promedio estimado calculado desde meses `ok`, con desglose disponible y excluyendo meses de remodelación

## Advertencias que debe mostrar 3D

- "Este módulo es experimental y orientativo; no representa contabilidad formal."
- advertencia de cobertura parcial OCR cuando `data_quality_flag == incomplete_ocr`
- advertencia de meses atípicos cuando `is_renovation_month == True`

## Limitaciones

- No representa P&L oficial ni utilidad neta.
- 2026 Q1 no tiene desglose categorizado suficiente en el parquet interim actual.
- La proyección de balance depende de gasto promedio operativo y no de una reconciliación contable completa.
- No asigna gastos por habitación.

## Qué debe hacer 3D

- Consumir `evaluate_historical_balance(...)` para tarjetas mensuales históricas.
- Consumir `project_monthly_balance(...)` para la vista de próximos 3 meses.
- Mostrar `warnings` de forma prominente y persistente.
- Presentar los resultados como "balance mensual estimado bajo supuestos", nunca como utilidad neta o estado financiero.
