"""Optional sklearn benchmarks (Yellow gate): linear + shallow tree, per currency."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.tree import DecisionTreeRegressor

from vitali.models.baseline_heuristic import _adr_native, _ensure_calendar, regression_metrics


def _design_matrix(df: pd.DataFrame, *, unit_categories: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    d = _ensure_calendar(df.copy())
    d["month"] = d["check_in_month"].astype(float)
    d["is_weekend"] = d["is_weekend"].astype(float)
    d["unit_id"] = pd.Categorical(d["unit_id"], categories=unit_categories)
    x_num = d[["month", "is_weekend"]].astype(float)
    x_u = pd.get_dummies(d["unit_id"], prefix="unit", dtype=float)
    X = pd.concat([x_num, x_u], axis=1)
    y = _adr_native(d)
    mask = y.notna() & X.notna().all(axis=1)
    return X.loc[mask], y.loc[mask]


@dataclass
class SklearnPhase5Result:
    name: str
    mae: float
    mape_pct: float
    r2: float


def eval_linear_and_tree(
    train: pd.DataFrame,
    val: pd.DataFrame,
    *,
    currency: str,
    tree_max_depth: int = 4,
) -> tuple[SklearnPhase5Result | None, SklearnPhase5Result | None]:
    """Fit on train, evaluate on val for one currency. Returns (linear, tree) or None if too few rows."""
    tr = train.loc[train["currency"] == currency]
    va = val.loc[val["currency"] == currency]
    if len(tr) < 8 or len(va) < 3:
        return None, None

    units = sorted(tr["unit_id"].dropna().unique().tolist())
    Xt, yt = _design_matrix(tr, unit_categories=units)
    Xv, yv = _design_matrix(va, unit_categories=units)
    Xv = Xv.reindex(columns=Xt.columns, fill_value=0.0)
    if Xt.shape[0] < 4 or Xv.shape[0] < 2:
        return None, None

    lin = LinearRegression().fit(Xt.to_numpy(), yt.to_numpy())
    pred_l = lin.predict(Xv.to_numpy())
    lin_res = SklearnPhase5Result(
        name="linear_regression",
        mae=regression_metrics(yv.to_numpy(), pred_l)["mae"],
        mape_pct=regression_metrics(yv.to_numpy(), pred_l)["mape_pct"],
        r2=float(r2_score(yv.to_numpy(), pred_l)),
    )

    tree = DecisionTreeRegressor(max_depth=tree_max_depth, random_state=42)
    tree.fit(Xt.to_numpy(), yt.to_numpy())
    pred_t = tree.predict(Xv.to_numpy())
    tree_res = SklearnPhase5Result(
        name=f"decision_tree_depth{tree_max_depth}",
        mae=regression_metrics(yv.to_numpy(), pred_t)["mae"],
        mape_pct=regression_metrics(yv.to_numpy(), pred_t)["mape_pct"],
        r2=float(r2_score(yv.to_numpy(), pred_t)),
    )
    return lin_res, tree_res
