# Inventario de datos y dataset MVP integrado para F7-MVP

## Resumen ejecutivo

- Conclusión: sí existe base suficiente para continuar a Fase C/F7 sin reprocesar XLSX ni OCR desde cero.
- Decisión operativa: Capa 1 debe construirse desde `data/interim/income_reservations_fx_crc_interim.parquet` en CRC normalizado, con apoyo de artifacts de tendencias y métricas.
- Decisión operativa: Capa 2 debe partir de `data/interim/reconcile_monthly_indicative.parquet` y `data/interim/expenses_all_years_interim.parquet`, declarando que el desglose categorizado hoy solo cubre 2025.
- Riesgo principal: el parquet interim de gastos no incluye 2026 Q1, aunque el perfil de gastos sí reporta esos meses; por eso los balances de 2026-01/02/03 quedan con bandera de calidad.

## Tarea 1 — Inventario real de artifacts

| Artifact | Ruta | Formato | Estado | Tamaño / filas | Columnas principales | Uso propuesto | Riesgos / advertencias |
|---|---|---|---|---|---|---|---|
| Parquet interim ingresos/reservas | `data/interim/income_reservations_fx_crc_interim.parquet` | parquet | existe (296 filas) | 30.9 KB | record_type, movement_date, booking_date, check_in, check_out, nights, unit_id, currency | Base canónica de Capa 1 y de agregados de ingreso mensual. | Mezcla CRC y USD normalizados a CRC; usar `unit_id` como llave canónica y no confundirlo con nombre comercial sin evidencia adicional. |
| Métricas baseline Fase 5 | `artifacts/baseline/phase5_metrics.json` | json | existe | 2.5 KB | input, n_train, n_val, use_lead_multipliers, by_currency, rules_doc, sklearn_benchmarks, complexity_decision | Respaldar la legitimidad del baseline heurístico y la narrativa de CRC como fuente principal. | No contiene segmentos por habitación/mes; es evidencia de desempeño, no dataset transaccional. |
| Métricas rolling Fase 6 | `artifacts/evaluation/phase6_rolling_metrics.json` | json | existe | 2.5 KB | method, dec_002_compliant, test_months_per_fold, n_folds_attempted, n_folds_executed, input, gate, folds | Contexto de confianza y advertencias por moneda para F7. | La señal rolling está agregada por moneda, no por segmento habitación×mes×contexto. |
| Income segment summary | `artifacts/income_segment_summary.json` | json | existe | 12.2 KB | summary_scope, by_unit_currency, by_month_currency, by_context_currency, by_lead_bucket_currency | Validar cobertura por unidad, moneda, mes y contexto. | Está agregado por moneda original; no reemplaza el cálculo CRC integrado por segmento del MVP. |
| Income segment insights | `artifacts/income_segment_insights.json` | json | existe | 8.8 KB | summary_scope, insight_count, primary_insight_count, appendix_insight_count, insights, primary_insights, appendix_insights | Reutilizar mensajes de confianza y gaps descriptivos para UI/documentación. | Los insights están a nivel narrativo; no traen una tabla lista para join por segmento. |
| Income trends tables | `artifacts/income_trends/tables/monthly_income_trends.csv` | csv | existe (40 filas) | 3.9 KB | check_in_year, check_in_month, unit_id, currency, reservations, nights, gross_income_sum, net_amount_sum | Apoyar tendencias y labels de habitación en visualizaciones futuras. | Son tablas agregadas auxiliares; no sustituyen el parquet interim ni cubren todos los joins necesarios. |
| Tabla income FX | `artifacts/income_analysis_table_fx.csv` | csv | existe (296 filas) | 65.3 KB | unit_id, currency, check_in, check_out, booking_date, movement_date, income_year, check_in_year | Referencia de columnas FX-normalizadas y validación de contrato upstream. | Útil como evidencia de schema; para F7 conviene consumir el parquet interim ya curado. |
| Parquet interim gastos | `data/interim/expenses_all_years_interim.parquet` | parquet | existe (327 filas) | 12.2 KB | source_file, source_sheet, fecha, descripcion, pagado_por, monto_crc, expense_year, expense_month | Base de categorías de gasto y escenarios Capa 2. | Contiene solo 2025 pese a que `expense_profile.json` reporta 2026 Q1; `expense_bucket` sigue siendo heurístico. |
| Parquet reconciliación mensual indicativa | `data/interim/reconcile_monthly_indicative.parquet` | parquet | existe (23 filas) | 7.3 KB | period, ingresos_gross_crc, ingresos_net_crc, n_bookings, egresos_crc, neto_gross_menos_egresos_crc, neto_net_menos_egresos_crc, year | Ingreso bruto mensual y egresos observados para balance mensual orientativo. | No es P&L formal; mezcla meses 2024 sin gastos y 2026 Q1 sin desglose categorizado. |
| Perfil de gastos | `artifacts/expense_profile.json` | json | existe | 3.1 KB | source_rows, source_files, date_range, by_source_file, by_month, top_descriptions | Validar cobertura temporal y advertencias de OCR/intake de gastos. | Es perfil agregado; no permite reconstruir categorías mensuales por sí solo. |

## Tarea 2 — Validación mínima de columnas

### Capa 1

- Dataset principal validado: `data/interim/income_reservations_fx_crc_interim.parquet`.
- Columnas encontradas: segment_key, unit_id, unit_display_name, month, is_weekend, adr_p25_crc, adr_median_crc, adr_p75_crc, gross_income_crc, n_reservations, n_nights, trend, confidence, confidence_reason, usd_context_only, usd_observations, crc_observations, data_sources.
- Cobertura directa confirmada: `unit_id`, `check_in_month`, `is_weekend`, `gross_adr_crc`, `gross_income_crc`, `nights`, `currency`.
- Columnas derivables: `confidence`, `confidence_reason`, `trend`, `usd_context_only`, `n_reservations`.
- Columnas faltantes no bloqueantes: ocupación real/capacidad instalada por habitación, soporte rolling por segmento fino.
- Observación: el artifact `income_segment_insights.json` sí incluye `confidence_label` y `confidence_reason`, pero no en formato tabular joinable por segmento; por eso se recalcula en el dataset derivado.

### Capa 2

- Datasets principales validados: `data/interim/expenses_all_years_interim.parquet`, `data/interim/reconcile_monthly_indicative.parquet`.
- Columnas encontradas en salida integrada: year, month, period, ingresos_gross_crc, ingresos_net_crc, n_bookings, expense_negocio_crc, expense_personal_crc, expense_shared_crc, expense_capex_crc, expense_dudoso_crc, expense_observed_total_crc, expense_total_conservative, expense_total_medium, expense_total_wide, balance_conservative, balance_medium, balance_wide, is_renovation_month, data_quality_flag, expense_breakdown_available, scenario_method.
- Cobertura directa confirmada: `year`, `month`, `ingresos_gross_crc`, `egresos_crc`/`expense_observed_total_crc`, `expense_bucket`, `descripcion`.
- Columnas derivables: separación `negocio/personal/compartido/capex/dudoso`, escenarios conservador/medio/amplio, `is_renovation_month`, `data_quality_flag`.
- Columnas faltantes no bloqueantes: fuente OCR por transacción, clasificación contable formal, asignación por habitación, reconciliación payout/comisiones exacta.
- Gap crítico documentado: el parquet interim de gastos hoy solo cubre 2025; los meses 2026-01/02/03 existen en `expense_profile.json` y en la reconciliación mensual, pero no con desglose categorizado en el parquet interim actual.

## Tarea 3 — Outputs preparados

| Output | Ruta | Descripción |
|---|---|---|
| Dataset Capa 1 | `data/processed/f7_capa1_price_ranges.parquet` | Segmentos por `unit_id × month × is_weekend` en CRC con rango histórico, tendencia y confianza. |
| Dataset Capa 2 | `data/processed/f7_capa2_monthly_balance.parquet` | Balance mensual orientativo con escenarios y banderas de calidad. |
| Proyección base | `artifacts/mvp/capa1_income_projection.json` | Rango histórico mensual bruto CRC para los próximos 3 meses calendario. |

## Contratos de salida propuestos

### Output 1 — `data/processed/f7_capa1_price_ranges.parquet`

- Grano: una fila por `unit_id × month × is_weekend`.
- Moneda operativa: CRC.
- Fuente primaria: `income_reservations_fx_crc_interim.parquet`.
- Advertencia contractual: `unit_display_name` reaprovecha el label visible en `artifacts/income_trends/tables/monthly_income_trends.csv`; `unit_id` sigue siendo la llave canónica.

### Output 2 — `data/processed/f7_capa2_monthly_balance.parquet`

- Grano: una fila por `year × month`.
- Fuente primaria: `reconcile_monthly_indicative.parquet` + `expenses_all_years_interim.parquet`.
- Regla de escenarios implementada:
  - conservador = negocio
  - medio = negocio + 50% compartido
  - amplio = negocio + compartido + personal
- Advertencia contractual: los escenarios solo se calculan donde existe desglose categorizado en el parquet interim; 2026 Q1 queda señalado como cobertura incompleta o atípica.

### Output 3 — `artifacts/mvp/capa1_income_projection.json`

- Horizonte: próximos 3 meses desde el último `check_in` observado.
- Método: percentiles históricos de ingreso bruto mensual CRC por mes calendario.
- Uso previsto: alimentar Prompt 3D con una proyección honesta y de baja complejidad.

## Evidencia de generación

- Filas Capa 1 generadas: 47.
- Filas Capa 2 generadas: 23.
- Meses proyectados: 3.
