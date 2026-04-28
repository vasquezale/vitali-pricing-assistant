"""Phase 6 — Rolling forward backtesting sobre BaselineHeuristicRules (gate Amarillo).

Método: expanding-window, 4 folds, test window = 2 meses (check_in).
Alineado con DEC-002: múltiples ventanas train→test, distribución de error.

Uso:
    uv run python scripts/rolling_forward_phase6.py
    uv run python scripts/rolling_forward_phase6.py --test-months 3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from vitali.models.baseline_heuristic import BaselineHeuristicRules, regression_metrics
from vitali.contracts.artifacts import ARTIFACTS


def _adr_native(df: pd.DataFrame) -> pd.Series:
    return df["gross_income"].astype(float) / df["nights"].replace({0: np.nan}).astype(float)


def build_expanding_windows(
    df: pd.DataFrame,
    *,
    test_months: int = 2,
    n_folds: int = 4,
    date_col: str = "check_in",
    min_train: int = 30,
) -> list[tuple[pd.DataFrame, pd.DataFrame, str, str]]:
    """Return list of (train, test, test_start_str, test_end_str) for expanding-window CV."""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col)

    date_min = df[date_col].min().to_period("M")
    date_max = df[date_col].max().to_period("M")
    total_months = (date_max - date_min).n + 1

    # last test fold ends at date_max; each fold shifts test window back by test_months
    windows = []
    for fold_idx in range(n_folds - 1, -1, -1):
        test_end = date_max - fold_idx * test_months
        test_start = test_end - test_months + 1

        test_start_ts = test_start.to_timestamp()
        test_end_ts = test_end.to_timestamp("M")

        train = df[df[date_col] < test_start_ts]
        test = df[(df[date_col] >= test_start_ts) & (df[date_col] <= test_end_ts)]

        if len(train) < min_train or len(test) == 0:
            continue

        windows.append((train, test, str(test_start), str(test_end)))

    return windows


def evaluate_fold(
    train: pd.DataFrame,
    test: pd.DataFrame,
    fold_label: str,
) -> dict:
    """Fit baseline on train, evaluate on test, return metrics dict."""
    model = BaselineHeuristicRules().fit(train)
    test_res = test[test["record_type"] == "reservation"].copy() if "record_type" in test.columns else test.copy()
    if test_res.empty:
        return {"fold": fold_label, "n_train": len(train), "n_test": 0, "by_currency": []}

    y_true = _adr_native(test_res)
    y_pred = model.predict(test_res)

    rows = []
    for cur in sorted(test_res["currency"].dropna().unique()):
        m = test_res["currency"] == cur
        yt = y_true.loc[m].to_numpy()
        yp = y_pred.loc[m].to_numpy()
        mask = pd.notna(yt) & pd.notna(yp)
        if mask.sum() == 0:
            continue
        met = regression_metrics(yt[mask], yp[mask])
        naive_val = float(np.median(yt[mask]))
        naive_pred = np.full_like(yt[mask], fill_value=naive_val, dtype=float)
        met_naive = regression_metrics(yt[mask], naive_pred)
        rows.append({
            "currency": cur,
            "n": int(mask.sum()),
            "mae": round(met["mae"], 4),
            "mape_pct": round(met["mape_pct"], 4),
            "mae_naive_median": round(met_naive["mae"], 4),
            "mae_improvement_vs_naive_pct": round(
                (met_naive["mae"] - met["mae"]) / met_naive["mae"] * 100 if met_naive["mae"] > 0 else 0.0, 2
            ),
        })

    return {
        "fold": fold_label,
        "n_train": int(len(train[train["record_type"] == "reservation"])) if "record_type" in train.columns else len(train),
        "n_test": int(sum(r["n"] for r in rows)),
        "by_currency": rows,
    }


def aggregate_metrics(fold_results: list[dict]) -> dict:
    """Summarize distribution of MAE/MAPE across folds per currency."""
    per_cur: dict[str, dict[str, list]] = {}
    for fold in fold_results:
        for row in fold.get("by_currency", []):
            cur = row["currency"]
            if cur not in per_cur:
                per_cur[cur] = {"mae": [], "mape_pct": [], "improvement_pct": []}
            per_cur[cur]["mae"].append(row["mae"])
            per_cur[cur]["mape_pct"].append(row["mape_pct"])
            per_cur[cur]["improvement_pct"].append(row["mae_improvement_vs_naive_pct"])

    summary = {}
    for cur, vals in per_cur.items():
        mae_arr = np.array(vals["mae"])
        mape_arr = np.array(vals["mape_pct"])
        imp_arr = np.array(vals["improvement_pct"])
        summary[cur] = {
            "n_folds_with_data": len(mae_arr),
            "mae_mean": round(float(mae_arr.mean()), 4),
            "mae_std": round(float(mae_arr.std()), 4),
            "mae_min": round(float(mae_arr.min()), 4),
            "mae_max": round(float(mae_arr.max()), 4),
            "mape_pct_mean": round(float(mape_arr.mean()), 4),
            "mape_pct_std": round(float(mape_arr.std()), 4),
            "mae_improvement_vs_naive_pct_mean": round(float(imp_arr.mean()), 2),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6 rolling forward backtesting.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--reservations-path", type=Path, default=None,
        help="Override parquet path (default: data/interim/income_reservations_fx_crc_interim.parquet)"
    )
    parser.add_argument("--test-months", type=int, default=2, help="Test window size in months per fold")
    parser.add_argument("--n-folds", type=int, default=4, help="Number of rolling folds")
    parser.add_argument("--min-train", type=int, default=30, help="Minimum reservation rows in train to include fold")
    args = parser.parse_args()

    root = args.root.resolve()
    path = args.reservations_path or (root / ARTIFACTS.income_reservations_fx_crc_interim_parquet)
    if not path.is_file():
        raise SystemExit(f"Missing parquet: {path}")

    df = pd.read_parquet(path)
    res_df = df[df["record_type"] == "reservation"].copy()

    windows = build_expanding_windows(
        res_df,
        test_months=args.test_months,
        n_folds=args.n_folds,
        min_train=args.min_train,
    )

    if not windows:
        raise SystemExit("No valid folds found. Try reducing --min-train or --test-months.")

    fold_results = []
    for train, test, ts, te in windows:
        label = f"{ts} → {te}"
        result = evaluate_fold(train, test, label)
        fold_results.append(result)

    summary = aggregate_metrics(fold_results)

    # Residual statistics across all folds
    all_errors: dict[str, list[float]] = {}
    for train, test, ts, te in windows:
        model = BaselineHeuristicRules().fit(train)
        test_res = test.copy()
        y_true = _adr_native(test_res)
        y_pred = model.predict(test_res)
        for cur in sorted(test_res["currency"].dropna().unique()):
            m = test_res["currency"] == cur
            yt = y_true.loc[m].to_numpy()
            yp = y_pred.loc[m].to_numpy()
            mask = pd.notna(yt) & pd.notna(yp)
            errs = (yt[mask] - yp[mask]).tolist()
            all_errors.setdefault(cur, []).extend(errs)

    residual_stats = {}
    for cur, errs in all_errors.items():
        arr = np.array(errs)
        residual_stats[cur] = {
            "n_total": len(arr),
            "mean_bias": round(float(arr.mean()), 4),
            "std": round(float(arr.std()), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p50": round(float(np.percentile(arr, 50)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
        }

    payload = {
        "method": "rolling_forward_expanding_window",
        "dec_002_compliant": True,
        "test_months_per_fold": args.test_months,
        "n_folds_attempted": args.n_folds,
        "n_folds_executed": len(fold_results),
        "input": str(path),
        "gate": "Amarillo",
        "folds": fold_results,
        "summary_by_currency": summary,
        "residual_stats_by_currency": residual_stats,
    }

    out_path = ARTIFACTS.resolve(root).phase6_rolling_metrics_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"\nSaved → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
