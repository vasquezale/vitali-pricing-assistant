# Income Segment Insights

These insights are derived mechanically from the segment summary and keep
`currency` as a mandatory dimension for every monetary comparison.

## Scope
- Source: `DatosVitali_ingresos_anonimizados.csv`
- Rows analyzed: `296`
- Currencies present: `CRC, USD`
- Units present: `room_a, room_b`
- FX statuses present: `original_currency_only`
- Insight count: `8`

## Insights
- [CRC] (high) room_b shows the highest median gross ADR at 77000.00, above room_a by 8000.00. Support: minimum segment support is 109 reservations across the compared units.
- [USD] (high) room_b shows the highest median gross ADR at 200.00, above room_a by 35.00. Support: minimum segment support is 34 reservations across the compared units.
- [CRC] (high) Weekend check-ins show higher median gross ADR than weekday check-ins by 17000.00. Support: minimum context support is 51 reservations across weekend vs weekday.
- [USD] (medium) Weekend check-ins show higher median gross ADR than weekday check-ins by 30.00. Support: minimum context support is 20 reservations across weekend vs weekday.
- [CRC] (high) The highest median gross ADR appears in lead bucket 31+ at 77000.00, versus 0-3 at 73500.00. Support: minimum bucket support is 34 reservations across the compared lead buckets.
- [USD] (low) The highest median gross ADR appears in lead bucket 31+ at 210.00, versus 0-3 at 162.50. Support: minimum bucket support is 3 reservations across the compared lead buckets.
- [CRC] (medium) The monthly peak median gross ADR appears in 2025-04 at 100000.00. Support: peak month segment contains 20 reservations.
- [USD] (medium) The monthly peak median gross ADR appears in 2025-12 at 207.50. Support: peak month segment contains 20 reservations.
