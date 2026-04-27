# Proyecto Vitali

**Pricing assistant and decision support system** for an Airbnb property in Cartago, Costa Rica.

> Analyzes historical reservation data to identify pricing patterns, seasonality, and profitability segments — then delivers actionable recommendations backed by evidence.

## Status

Early development. Project scaffolding is in place, Phase 1 is still being closed, and Phase 2 remains blocked until Airbnb raw data is available locally under `data/raw/`.

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

1. Place the sanitized CSV at `data/external/DatosVitali_ingresos_anonimizados.csv`
   or pass a custom path with `--input`.
2. Generate a compact JSON profile:

```bash
uv run python scripts/profile_income_data.py \
  --input /absolute/path/to/DatosVitali_ingresos_anonimizados.csv \
  --output artifacts/income_profile.json
```

This step validates the extract, parses dates, preserves the mixed `USD` / `CRC`
context, and emits a profile segmented by currency and room identifier.

To generate a more analytical descriptive summary:

```bash
uv run python scripts/summarize_income_data.py \
  --input /absolute/path/to/DatosVitali_ingresos_anonimizados.csv \
  --json-output artifacts/income_summary.json \
  --markdown-output artifacts/income_summary.md
```

This summary stays within the current project guardrails: it is descriptive and
reproducible, but it is not a substitute for profitability modeling, market
analysis, or a formal Fase 2 gate.

To build a reservation-level analysis table for downstream EDA:

```bash
uv run python scripts/build_income_analysis_table.py \
  --input /absolute/path/to/DatosVitali_ingresos_anonimizados.csv \
  --output artifacts/income_analysis_table.csv
```

This table preserves original currency by default and does not invent exchange
rates. If you later decide on explicit normalization inputs, you can pass them
deliberately:

```bash
uv run python scripts/build_income_analysis_table.py \
  --input /absolute/path/to/DatosVitali_ingresos_anonimizados.csv \
  --output artifacts/income_analysis_table.csv \
  --fx-rates-json '{"USD":510.0,"CRC":1.0}'
```

The same policy can be declared in [configs/base.yaml](/Users/ale/Documents/GitHub_Repositorios/proyecto-vitali/configs/base.yaml)
under `fx_normalization`. The recommended default for the current phase is:

- `enabled: false`
- `strategy: preserve_original`

Only switch to `manual_static` when you have explicitly chosen and documented
the rates you want to use for comparison in CRC.

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
