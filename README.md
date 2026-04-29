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

---

## Dashboard — F7 MVP

An interactive decision-support dashboard built with Streamlit and Plotly. Provides actionable pricing guidance and a monthly balance estimate for property managers, with no manual spreadsheet work required.

### What it shows

**Executive Summary** — Key business metrics at a glance: median ADR by unit, peak demand month, reservation count, monthly income trend, and projected balance under a conservative scenario.

**Pricing Layer (Capa 1)** — Context-aware price reference by unit, month, and day type (weekday vs. weekend). Includes observed price ranges (p25–p75), support count, and an optional comparison against a manually entered price.

**Balance Layer (Capa 2)** — Monthly estimated balance: gross income vs. estimated expenses across three cost scenarios (conservative, medium, wide), with projected forward-looking balance curve.

**History & Trends** — Monthly income evolution by unit and currency, median ADR over time, and a reservations heatmap to identify seasonal demand concentration.

**Evaluation** — Rolling-forward validation metrics for the baseline model, with explicit methodology warnings (Yellow Gate).

### Screenshots

| Executive Summary | Pricing Reference | History & Trends |
|---|---|---|
| ![Executive Summary](docs/screenshots/01_resumen_ejecutivo.png) | ![Pricing Layer](docs/screenshots/02_capa_precio.png) | ![Trends](docs/screenshots/03_historia_tendencias.png) |

### How to run

```bash
uv sync
uv run streamlit run src/vitali/dashboard/app.py
```

The app loads from local gitignored data files. No API keys or external services required.

> **Methodology note:** This dashboard is a decision-support tool, not an automatic pricing engine or formal financial statement. All monetary recommendations include explicit uncertainty ranges and Yellow Gate warnings where applicable.
