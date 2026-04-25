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
