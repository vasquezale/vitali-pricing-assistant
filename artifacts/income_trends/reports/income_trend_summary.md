# Income Trend Visual Summary

- Source: `Ingresos_Vitali_ingresos_anonimizados.csv`
- Rows analyzed: `296`
- Currencies present: `CRC, USD`
- Units present: `CieloRosa, Aqua`
- Check-in range: `2024-05-04` to `2026-01-30`

## Quick Reading Guide
- `monthly_reservations_by_room.png`: how bookings evolve over time by room.
- `monthly_gross_income_by_room.png`: how gross income moves over time by room.
- `monthly_median_adr_by_room.png`: how typical nightly rate changes by room.
- `monthly_context_adr.png`: whether weekend check-ins tend to outperform weekdays by month.

## Highest Monthly Peaks by Currency and Room
- `CRC` / `CieloRosa`: max reservations in `2024-12` (16), max gross income in `2024-12` (1110000.00), max median ADR in `2025-04` (100000.00).
- `CRC` / `Aqua`: max reservations in `2025-07` (14), max gross income in `2025-04` (1330000.00), max median ADR in `2025-04` (100000.00).
- `USD` / `CieloRosa`: max reservations in `2025-12` (9), max gross income in `2025-12` (1931.00), max median ADR in `2025-12` (200.00).
- `USD` / `Aqua`: max reservations in `2025-11` (12), max gross income in `2025-11` (2730.00), max median ADR in `2025-12` (220.00).

## Caveats
- The charts keep `currency` separated on purpose; do not compare `USD` and `CRC` values directly.
- These visuals describe observed income behavior, not causal effects.
- Months with few reservations can show sharp jumps in ADR.
