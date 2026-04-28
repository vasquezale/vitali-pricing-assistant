"""Phase 5 — baseline heurístico + benchmarks opcionales (gate Amarillo).

Entrada por defecto: `data/interim/income_reservations_fx_crc_interim.parquet`
(generado junto con `prepare_phase3_datasets.py`).

Uso:
    uv run python scripts/prepare_phase3_datasets.py
    uv run python scripts/baseline_rules_phase5.py
    uv run python scripts/baseline_rules_phase5.py --compare-sklearn
    uv run python scripts/baseline_rules_phase5.py --use-lead-multipliers  # escenario no ex-ante
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from vitali.models.baseline_heuristic import BaselineHeuristicRules, regression_metrics, temporal_train_val_split
from vitali.models.sklearn_phase5 import eval_linear_and_tree
from vitali.contracts.artifacts import ARTIFACTS


def default_reservations_path(root: Path) -> Path:
    interim = root / ARTIFACTS.income_reservations_fx_crc_interim_parquet
    fallback = root / ARTIFACTS.income_reservations_fx_crc_sanitized_parquet
    if interim.is_file():
        return interim
    return fallback


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5 baseline rules + optional sklearn comparison.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--reservations-path", type=Path, default=None, help="Override parquet path")
    parser.add_argument("--val-frac", type=float, default=0.2)
    parser.add_argument("--compare-sklearn", action="store_true")
    parser.add_argument(
        "--use-lead-multipliers",
        action="store_true",
        help="Apply lead_bucket multipliers (NOT ex-ante; backtest al día de reserva solamente).",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.reservations_path or default_reservations_path(root)
    if not path.is_file():
        raise SystemExit(f"Missing reservations parquet: {path}. Run scripts/prepare_phase3_datasets.py first.")

    df = pd.read_parquet(path)
    df = df.loc[df["record_type"] == "reservation"].copy()
    train, val = temporal_train_val_split(df, val_frac=args.val_frac)

    baseline = BaselineHeuristicRules().fit(train, use_lead_multipliers=args.use_lead_multipliers)
    pred_val = baseline.predict(val)
    y_val = val["gross_income"].astype(float) / val["nights"].replace({0: float("nan")}).astype(float)

    out_dir = (root / ARTIFACTS.phase5_metrics_json).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for cur in sorted(val["currency"].dropna().unique()):
        m = val["currency"] == cur
        yt = y_val.loc[m].to_numpy()
        yp = pred_val.loc[m].to_numpy()
        mask = pd.notna(yt) & pd.notna(yp)
        if mask.sum() == 0:
            continue
        met = regression_metrics(yt[mask], yp[mask])
        naive = float(pd.Series(yt[mask]).median())
        naive_pred = np.full_like(yt[mask], fill_value=naive, dtype=float)
        met_naive = regression_metrics(yt[mask], naive_pred)
        rows.append(
            {
                "currency": cur,
                "n_val": int(mask.sum()),
                "mae_baseline": met["mae"],
                "mape_pct_baseline": met["mape_pct"],
                "mae_naive_median": met_naive["mae"],
            }
        )

    payload = {
        "input": str(path),
        "n_train": int(len(train)),
        "n_val": int(len(val)),
        "use_lead_multipliers": bool(args.use_lead_multipliers),
        "by_currency": rows,
        "rules_doc": (
            "L1 median ADR by (currency, unit_id, check_in_month, is_weekend); "
            "fallback L2 (currency, unit_id, is_weekend); L3 (currency, unit_id); L4 (currency). "
            "Features: Sí ex-ante per research/03. EDA refs: research/04 §6 findings 1–3 (unit, weekend)."
        ),
    }

    if args.compare_sklearn:
        sk_rows = []
        for cur in sorted(val["currency"].dropna().unique()):
            lin, tree = eval_linear_and_tree(train, val, currency=str(cur))
            if lin is not None:
                sk_rows.append({"currency": cur, **vars(lin)})
            if tree is not None:
                sk_rows.append({"currency": cur, **vars(tree)})
        payload["sklearn_benchmarks"] = sk_rows

        for cur in sorted(val["currency"].dropna().unique()):
            m = val["currency"] == cur
            yt = y_val.loc[m].to_numpy()
            yp = pred_val.loc[m].to_numpy()
            mask = pd.notna(yt) & pd.notna(yp)
            if mask.sum() == 0:
                continue
            mae_b = regression_metrics(yt[mask], yp[mask])["mae"]
            lin, tree = eval_linear_and_tree(train, val, currency=str(cur))
            for name, res in (("linear", lin), ("tree", tree)):
                if res is None:
                    continue
                improve = (mae_b - res.mae) / mae_b if mae_b > 0 else 0.0
                payload.setdefault("complexity_decision", []).append(
                    {
                        "currency": cur,
                        "model": name,
                        "mae_model": res.mae,
                        "mae_baseline": mae_b,
                        "relative_mae_improvement": round(float(improve), 4),
                        "r2": res.r2,
                        "adopt_if_improvement_ge_0.1": bool(improve >= 0.1),
                    }
                )

    ARTIFACTS.resolve(root).phase5_metrics_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
