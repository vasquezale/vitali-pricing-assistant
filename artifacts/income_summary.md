# Income Summary

This report is a reproducible descriptive summary of the anonymized income extract.
It is useful for technical preparation and business orientation, but it is not a substitute
for Fase 1 closeout, profitability analysis, or a full Fase 2 viability gate.

## Scope
- Source: `DatosVitali_ingresos_anonimizados.csv`
- Reservation rows analyzed: `296`
- Currencies present: `CRC, USD`
- Units present: `room_a, room_b`
- Check-in range: `2024-05-04` to `2026-01-30`

## By Unit and Currency
| unit_id | currency | reservations | nights | median_gross_adr | median_net_adr | median_booking_lead_days |
|---|---|---:|---:|---:|---:|---:|
| room_a | CRC | 109 | 116 | 69000.00 | 66660.90 | 10.0 |
| room_a | USD | 34 | 41 | 165.00 | 159.41 | 9.5 |
| room_b | CRC | 116 | 128 | 77000.00 | 74392.11 | 14.5 |
| room_b | USD | 37 | 43 | 200.00 | 193.22 | 9.0 |

## Weekend vs Weekday Check-in
| currency | check_in_context | reservations | nights | median_gross_adr | median_net_adr |
|---|---|---:|---:|---:|---:|
| CRC | weekday | 51 | 58 | 60000.00 | 57967.93 |
| CRC | weekend | 174 | 186 | 77000.00 | 74389.70 |
| USD | weekday | 20 | 26 | 150.00 | 144.92 |
| USD | weekend | 51 | 58 | 180.00 | 173.90 |

## Booking Lead Buckets
| currency | lead_bucket | reservations | nights | median_gross_adr | median_net_adr |
|---|---|---:|---:|---:|---:|
| CRC | 0-3 | 34 | 37 | 73500.00 | 71008.35 |
| CRC | 15-30 | 69 | 73 | 70000.00 | 67627.00 |
| CRC | 31+ | 37 | 43 | 77000.00 | 74389.70 |
| CRC | 4-7 | 43 | 45 | 70000.00 | 67627.02 |
| CRC | 8-14 | 42 | 46 | 77000.00 | 74389.70 |
| USD | 0-3 | 21 | 26 | 162.50 | 156.99 |
| USD | 15-30 | 16 | 18 | 190.00 | 183.56 |
| USD | 31+ | 3 | 4 | 210.00 | 202.88 |
| USD | 4-7 | 6 | 7 | 190.00 | 183.56 |
| USD | 8-14 | 25 | 29 | 180.00 | 173.90 |

## Check-in Weekday Detail
| currency | check_in_weekday | reservations | median_gross_adr |
|---|---|---:|---:|
| CRC | Monday | 11 | 60000.00 |
| CRC | Tuesday | 5 | 60000.00 |
| CRC | Wednesday | 13 | 60000.00 |
| CRC | Thursday | 22 | 69500.00 |
| CRC | Friday | 51 | 77000.00 |
| CRC | Saturday | 90 | 77000.00 |
| CRC | Sunday | 33 | 70000.00 |
| USD | Monday | 5 | 150.00 |
| USD | Tuesday | 4 | 173.75 |
| USD | Wednesday | 7 | 140.00 |
| USD | Thursday | 4 | 175.00 |
| USD | Friday | 15 | 185.00 |
| USD | Saturday | 26 | 180.00 |
| USD | Sunday | 10 | 158.75 |
