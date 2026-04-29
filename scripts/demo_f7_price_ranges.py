from __future__ import annotations

from pprint import pprint

from vitali.mvp.price_ranges import evaluate_price


def main() -> None:
    examples = [
        ("room_a", 2, "weekend", 65000.0),
        ("room_b", 1, "weekday", 90000.0),
    ]
    for unit_id, month, day_type, price in examples:
        print("=" * 80)
        pprint(evaluate_price(unit_id, month, day_type, price))


if __name__ == "__main__":
    main()
