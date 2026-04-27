# Data Dictionary

## Purpose
- Document the minimum stable semantics validated during Phase 2.
- Support reproducible analysis without promoting unvalidated business assumptions.
- Preserve the current `preserve_original` currency policy.

## Status
- Status: Active working dictionary
- Last validated: 2026-04-27
- Scope: income CSV, expense workbook intake, and current repo-level parsed fields

## Rules
- Do not aggregate `CRC` and `USD` monetary fields without an explicit FX policy.
- Do not treat `room_a` and `room_b` as formally equivalent to `CieloRosa` and `Aqua` unless a documentary source closes that mapping.
- Do not treat expense descriptions as a final accounting taxonomy; current labels support profiling and guarded heuristics only.

## Income Source
Source file:
- `data/raw/airbnb/Ingresos_Vitali_ingresos_anonimizados.csv`

Parsed by:
- `src/vitali/data/income.py`

### Raw / validated income fields
| Field | Type | Meaning | Notes |
|---|---|---|---|
| `record_type` | string | Row type in the Airbnb extract | Allowed values now: `reservation`, `resolution_payment` |
| `movement_date` | date | Ledger movement or payout-related date | Parsed to datetime |
| `booking_date` | date | Booking creation date | Missing on `resolution_payment` rows |
| `check_in` | date | Stay start date | Required for reservations |
| `check_out` | date | Stay end date | Required for reservations |
| `nights` | numeric | Stay length in nights | Positive for reservations |
| `unit_id` | string | Unit identifier present in the extract | Observed values: `room_a`, `room_b` |
| `currency` | string | Original transaction currency | Observed values: `CRC`, `USD` |
| `net_amount` | numeric | Net amount after service fee in original currency | Present on all observed rows |
| `service_fee` | numeric | Airbnb service fee in original currency | Missing on `resolution_payment` rows |
| `quick_pay_fee` | numeric | Quick-pay fee | Currently empty in all observed rows |
| `cleaning_fee` | numeric | Cleaning component in original currency | `CRC` rows show `0.0`; `USD` rows show `0.0` or `20.0` |
| `gross_income` | numeric | Gross amount before service fee in original currency | Present on all observed rows |
| `lodging_tax` | numeric | Lodging tax amount | Currently empty or zero in observed data |
| `income_year` | numeric | Year field supplied in the extract | Useful as context, not canonical date logic |
| `booking_lead_days` | numeric | Days between booking and check-in | Missing on `resolution_payment` rows |

### Derived income metrics used in repo artifacts
| Field | Type | Meaning | Notes |
|---|---|---|---|
| `gross_adr` | numeric | `gross_income / nights` | Must stay within original currency |
| `net_adr` | numeric | `net_amount / nights` | Must stay within original currency |
| `service_fee_rate` | numeric | `service_fee / gross_income` | Stable near 3.39% in observed data |
| `check_in_context` | string | Weekday / weekend grouping | Derived from `check_in` day-of-week |
| `lead_bucket` | string | Lead time bucket | Derived from `booking_lead_days` |

## Expense Source
Source files:
- `data/raw/financials/FINCA VITALI _ Contabilidad Administrativa _ 2025.xlsx`
- `data/raw/financials/FINCA VITALI _ Contabilidad Administrativa _ 2026.xlsx`

Parsed by:
- `src/vitali/data/expenses.py`

### Workbook structure notes
- `2025` contains monthly sheets with an `EGRESOS` block and partial income blocks for `CIELO ROSA` and `AQUA`.
- `2026 Q1` is structurally dominated by `EGRESOS`.
- The current repo parser intentionally ingests only the expense-side block.

### Parsed expense fields
| Field | Type | Meaning | Notes |
|---|---|---|---|
| `source_file` | string | Workbook file name | Preserves year source |
| `source_sheet` | string | Monthly sheet name | Expected values are Spanish month names |
| `expense_date` | date | Parsed transaction date | Some rows remain null |
| `description` | string | Original free-text description | Some rows remain null; not a final taxonomy |
| `paid_by` | string | Payer / payment-type field from workbook | Mostly `Pablo`; can also reflect other labels |
| `amount_crc` | numeric | Parsed expense amount in CRC | Required in current intake |
| `expense_year` | numeric | Inferred year | From parsed date or workbook name |
| `expense_month` | numeric | Inferred month number | Derived from sheet name |

## Current Analytical Use Guidance
- Income data is ready for reproducible descriptive analysis by reservation, month, unit, and currency-separated ADR/lead-time views.
- Expense data is ready for reproducible intake, profiling, and guarded category review.
- Strong profitability outputs by reservation, night, or unit are not yet supported by the validated semantics above.
