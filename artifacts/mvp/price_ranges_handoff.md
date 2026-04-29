# Handoff — Capa 1 Price Ranges

## Módulo creado

- Ruta: `src/vitali/mvp/price_ranges.py`
- API principal: `evaluate_price(unit_id, month, day_type, current_price_crc, *, repo_root=None, dataset_path=None) -> dict`
- Helper de carga: `load_price_ranges(...) -> pandas.DataFrame`

## Dataset usado

- Fuente principal: `data/processed/f7_capa1_price_ranges.parquet`
- Artifact auxiliar permitido: `artifacts/mvp/capa1_income_projection.json`

## Columnas requeridas

- `unit_id`
- `unit_display_name`
- `month`
- `is_weekend`
- `adr_p25_crc`
- `adr_median_crc`
- `adr_p75_crc`
- `trend`
- `confidence`
- `confidence_reason`
- `n_reservations`
- `usd_context_only`

## Reglas implementadas

- `por_debajo`: `current_price_crc < adr_p25_crc`
- `dentro_del_rango`: `adr_p25_crc <= current_price_crc <= adr_p75_crc`
- `por_encima`: `current_price_crc > adr_p75_crc`
- `sin_referencia_suficiente`: error explícito cuando el segmento no existe en el dataset

## Ejemplo de uso

```python
from vitali.mvp.price_ranges import evaluate_price

result = evaluate_price(
    unit_id="room_a",
    month=2,
    day_type="weekend",
    current_price_crc=65000,
)
```

## Limitaciones

- El evaluador no construye dashboard ni visuales.
- La recomendación principal es solo en CRC.
- El uso de USD se limita a advertencia contextual cuando `usd_context_only=True`.
- `unit_id` es la llave canónica; `unit_display_name` es para presentación.
- Si el dataset derivado cambia de schema, `load_price_ranges` falla de forma explícita.

## Qué debe hacer 3D

- Consumir `evaluate_price(...)` desde la UI en vez de reimplementar lógica de comparación.
- Mostrar `warnings` como bloque visible en pantalla.
- Mantener `room_a` y `room_b` separados en todo selector o visual.
- Reusar `price_position`, `confidence_label`, `trend_label` y `message` como salida primaria de la tarjeta operativa.
