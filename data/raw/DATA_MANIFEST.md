# Data Manifest — Finca Vitali

## Fuentes de datos

### Gastos (EGRESOS)
- **2025**: `data/raw/2025/expenses_2025_raw.xlsx`
  - Origen: `/Users/ale/Documents/Personal/Datos_Vitali/FINCA VITALI _ Contabilidad Administrativa _ 2025.xlsx`
  - Cobertura: Enero–Diciembre 2025 (12 meses)
  - Estructura: Columnas [Fecha, Descripción, Pagado por, Monto]
  - Formato: XLSX (múltiples sheets por mes)
  - Source-of-truth: SÍ (dinámico; OCR de PDF validado)

- **2026**: `data/raw/2026/expenses_2026_raw.xlsx`
  - Origen: `/Users/ale/Documents/Personal/Datos_Vitali/FINCA VITALI _ Contabilidad Administrativa _ 2026.xlsx`
  - Cobertura: Enero–Marzo 2026 (3 meses, parcial)
  - Estructura: Columnas [Fecha, Descripción, Pagado por, Monto, Tipo]
  - Formato: XLSX
  - Source-of-truth: SÍ

### Ingresos (INGRESOS)
- **income_analysis_table_fx.csv** (en repo `/artifacts/`)
  - Origen: Airbnb API extraída a Numbers, exportada a CSV
  - Cobertura: Mayo 2024 – Enero 2026
  - Estructura: [unit_id, currency, check_in, check_out, gross_income_crc, net_amount_crc, ...]
  - Formato: CSV limpio
  - Source-of-truth: SÍ (con conversión USD→CRC aplicada)

## Decisiones Fase 2

| Decisión | Valor |
|----------|-------|
| ¿XLSX en Git? | SÍ — data/raw/{2025,2026}/ |
| ¿CSV generados? | SÍ — generarlos en pipeline (pandas/polars) |
| ¿Vault financials es source? | NO — es análisis derivado; source es data/raw/ |
| ¿Validación requerida? | SÍ — tests de integridad en Fase 2 |

## Pipeline esperado (Fase 2)

```
data/raw/
  ├─ 2025/expenses_2025_raw.xlsx → load_expenses(2025)
  ├─ 2026/expenses_2026_raw.xlsx → load_expenses(2026)
  └─ income_analysis_table_fx.csv (repo) → load_income()
         ↓
    validate_data()
         ↓
    reconcile_monthly() → DataFrame[mes, ingresos, egresos, neto]
         ↓
    tests/ (data quality)
         ↓
    artifacts/ (outputs)
```

Última actualización: 2026-04-27
