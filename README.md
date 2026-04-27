# Proyecto Vitali

**Pricing assistant and decision support system** for an Airbnb property in Cartago, Costa Rica.

> Analyzes historical reservation data to identify pricing patterns, seasonality, and profitability segments — then delivers actionable recommendations backed by evidence.

## Status

Project scaffolding is in place, Phase 1 is closed with explicit reservations, and
Phase 2 can now start from the currently available local `data/raw/` sources.
What remains uncertain is not file placement, but whether the available scope is
enough for a green, yellow, or red gate decision.

## Repo vs Vault

This repository is intentionally limited to **practical, executable project assets**:

- production code,
- tests,
- configuration,
- scripts,
- lightweight artifacts needed for delivery.

Project context, research, agent coordination, prompts, and living documentation are kept in the private vault outside the repository.

## Privacy and Data Handling

- Real Airbnb exports, guest data, sanitized datasets, and intermediate datasets must stay under `data/` and are never committed.
- Secrets, local credentials, and personal tooling files must stay in ignored locations such as `.env`, `secrets/`, or repo-local excludes.
- If a file should help other collaborators without exposing secrets, commit a safe template such as `.env.example` instead of the real file.

## What `data/raw/` Means Here

`data/raw/` does **not** mean “more private data must exist somewhere else”.
It means the real source files you already have should be copied into a stable,
ignored, repo-local structure so scripts can reference them reproducibly.

Recommended local layout:

```text
data/
  raw/
    financials/
      FINCA VITALI _ Contabilidad Administrativa _ 2025.xlsx
      FINCA VITALI _ Contabilidad Administrativa _ 2026.xlsx
    airbnb/
      Ingresos_Vitali_ingresos_anonimizados.csv
```

The files stay local and gitignored. The value is reproducibility, not publication.

## Quick Start

```bash
# Setup environment
uv sync
uv sync --extra dev

# Run quality checks
uv run bash scripts/run_quality_checks.sh
```

## Reproducible Income Analysis Base

The project now includes a minimal reproducible path for the anonymized income extract.

1. Place the local CSV at `data/raw/airbnb/Ingresos_Vitali_ingresos_anonimizados.csv`
   or pass a custom path with `--input`.
2. Generate a compact JSON profile:

```bash
uv run python scripts/profile_income_data.py \
  --input /absolute/path/to/Ingresos_Vitali_ingresos_anonimizados.csv \
  --output artifacts/income_profile.json
```

This step validates the extract, parses dates, preserves the mixed `USD` / `CRC`
context, and emits a profile segmented by currency and room identifier.

To generate a more analytical descriptive summary:

```bash
uv run python scripts/summarize_income_data.py \
  --input /absolute/path/to/Ingresos_Vitali_ingresos_anonimizados.csv \
  --json-output artifacts/income_summary.json \
  --markdown-output artifacts/income_summary.md
```

This summary stays within the current project guardrails: it is descriptive and
reproducible, but it is not a substitute for profitability modeling, market
analysis, or a formal Fase 2 gate.

To build a reservation-level analysis table for downstream EDA:

```bash
uv run python scripts/build_income_analysis_table.py \
  --input /absolute/path/to/Ingresos_Vitali_ingresos_anonimizados.csv \
  --output artifacts/income_analysis_table.csv
```

This table preserves original currency by default and does not invent exchange
rates. If you later decide on explicit normalization inputs, you can pass them
deliberately:

```bash
uv run python scripts/build_income_analysis_table.py \
  --input /absolute/path/to/Ingresos_Vitali_ingresos_anonimizados.csv \
  --output artifacts/income_analysis_table.csv \
  --fx-rates-json '{"USD":510.0,"CRC":1.0}'
```

The same policy can be declared in [configs/base.yaml](/Users/ale/Documents/GitHub_Repositorios/proyecto-vitali/configs/base.yaml)
under `fx_normalization`. The recommended default for the current phase is:

- `enabled: false`
- `strategy: preserve_original`

Only switch to `manual_static` when you have explicitly chosen and documented
the rates you want to use for comparison in CRC.

To generate an aggregated summary that keeps `currency` as a mandatory grouping
axis for monetary metrics:

```bash
uv run python scripts/summarize_income_segments.py \
  --input /absolute/path/to/Ingresos_Vitali_ingresos_anonimizados.csv \
  --json-output artifacts/income_segment_summary.json \
  --markdown-output artifacts/income_segment_summary.md
```

This is the recommended next step under the current official policy
`preserve_original`, because it allows totals and medians by segment without
accidentally mixing `USD` and `CRC`.

To derive reproducible narrative insights from those segments:

```bash
uv run python scripts/generate_income_segment_insights.py \
  --input /absolute/path/to/Ingresos_Vitali_ingresos_anonimizados.csv \
  --json-output artifacts/income_segment_insights.json \
  --markdown-output artifacts/income_segment_insights.md
```

These insights are generated from the segment summary itself. They are meant to
reduce manual reading of raw tables, not to replace deeper business validation.

To generate quick visual diagnostics of how income behaves over time by room:

```bash
uv run python scripts/plot_income_trends.py \
  --input /absolute/path/to/Ingresos_Vitali_ingresos_anonimizados.csv \
  --output-dir artifacts/income_trends
```

This produces:

- `charts/`: PNG charts for monthly reservations, gross income, median ADR, and month/context ADR
- `tables/`: CSV support tables for the plotted series
- `reports/`: compact Markdown and JSON summaries for fast reading

Keep in mind that the charts still respect the current `preserve_original`
currency policy, so `USD` and `CRC` are shown separately.

## Reproducible Expense Analysis Base

The repo now also includes a minimal reproducible path for the accounting
workbooks used as the expense source of truth.

1. Copy the real workbooks into `data/raw/financials/`, or pass explicit paths
   with repeated `--input` flags.
2. Generate a compact profile:

```bash
uv run python scripts/profile_expense_data.py \
  --input "/absolute/path/to/FINCA VITALI _ Contabilidad Administrativa _ 2025.xlsx" \
  --input "/absolute/path/to/FINCA VITALI _ Contabilidad Administrativa _ 2026.xlsx" \
  --output artifacts/expense_profile.json
```

This step does **not** solve cost allocation or net profitability. It only gives
the project a reproducible expense intake layer so Fase 2 does not start from
Markdown summaries alone.

## Safe Publication Flow

```bash
# 1. Work from the public-safe branch
git switch codex/public-ready

# 2. Run quality checks
uv run bash scripts/run_quality_checks.sh

# 3. Run the pre-push security review
bash scripts/pre_push_security_check.sh
```

Create the first GitHub remote from `codex/public-ready`, never from `main`.

## Project Structure

```
src/vitali/     — Production code
tests/          — Pytest test suite
configs/        — YAML configuration
scripts/        — Operational scripts and quality checks
artifacts/      — Lightweight tracked artifacts only
data/           — Local-only datasets (gitignored)
```

## Methodology

CRISP-DM adapted with a **data viability gate** — if the data doesn't support ML, the project delivers analytical rules and descriptive insights (still valuable).
