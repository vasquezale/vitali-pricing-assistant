# Airbnb Demand & Pricing Analytics

**Decision-support analytics product** that turns raw Airbnb reservation history into pricing guidance, demand insights, and business-facing visualizations for non-technical users.

Built with real business data from a short-term rental property in Cartago, Costa Rica (`296 reservations` · `2 units` · `~2 years of data`).

---

## What it does

Takes raw, anonymized reservation exports and translates them into three business outputs:

- **Demand patterns** — identifies which months, day types, and units drive stronger commercial performance
- **Pricing reference** — provides context-aware price ranges by unit, month, and weekday vs. weekend based on observed historical behavior
- **Balance estimates** — compares monthly gross income against estimated expenses across multiple cost scenarios

All outputs are surfaced through an interactive dashboard designed for decision support rather than black-box automation.

---

## Dashboard

Main views in the current demo:

- **Business Summary** — key metrics at a glance: nightly median rate, top-performing unit, peak month, total reservations, income trend, and projected balance
- **Pricing Reference** — select unit, month, and day type to get an observed price range with historical support count; compare against a custom price
- **Monthly Balance** — income vs. estimated expenses with three cost scenarios; projected forward balance curve
- **History & Trends** — income evolution over time, nightly rate by unit, and a reservations heatmap

Technical evaluation is optional and only shown when technical artifacts are available.

---

## Why this project is interesting

- Built from a real hospitality decision problem, not a toy dataset
- Connects data cleaning, analytics, business logic, and product delivery in one pipeline
- Frames outputs for an operational user who needs guidance, not ML jargon
- Preserves privacy by keeping raw reservation data anonymized and gitignored

## Example findings

- **Weekend check-ins command ~22% higher daily rates** than weekday check-ins
- **One unit consistently outperforms the other** by roughly `CRC 8,000` in median daily rate
- **Peak demand concentrates in April and December**, revealing strong seasonal pricing windows
- **Longer booking lead times correlate with slightly higher rates**, suggesting a usable pricing lever

---

## Tech stack

| Layer | Tools |
|---|---|
| Data processing | Python · pandas · NumPy |
| Modeling | scikit-learn · statistical baseline |
| Dashboard | Streamlit · Plotly |
| Testing | pytest · TDD throughout |
| Environment | uv · pyproject.toml |

---

## Run it locally

```bash
# 1. Clone and install dependencies
git clone https://github.com/vasquezale/vitali-pricing-assistant.git
cd vitali-pricing-assistant
uv sync

# 2. Launch the dashboard
uv run streamlit run src/vitali/dashboard/app.py
```

> The app loads from local data files (gitignored for privacy). The dashboard structure, pipeline logic, and analytical code run without external APIs or cloud dependencies.

---

## Project structure

```
src/vitali/    — core package
  data/        — loaders, validators, cleaning pipeline
  dashboard/   — Streamlit app and Plotly chart factories
  mvp/         — pricing and balance business logic
  models/      — baseline model and evaluation utilities
tests/         — pytest suite
scripts/       — reproducible pipeline scripts
artifacts/     — tracked analytical outputs
configs/       — YAML configuration
```

---

## Privacy

Real reservation data is anonymized and gitignored. Only production code and safe analytical artifacts are committed to this repository.
