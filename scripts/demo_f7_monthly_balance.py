from __future__ import annotations

from pprint import pprint

from vitali.mvp.monthly_balance import evaluate_historical_balance, project_monthly_balance


def main() -> None:
    print("=" * 80)
    pprint(evaluate_historical_balance(2025, 10, "conservative"))
    print("=" * 80)
    pprint(evaluate_historical_balance(2026, 2, "medium"))
    print("=" * 80)
    for item in project_monthly_balance("wide"):
        pprint(item)


if __name__ == "__main__":
    main()
