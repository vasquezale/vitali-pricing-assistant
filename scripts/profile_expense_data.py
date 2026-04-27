"""Generate a compact profile for the local expense workbooks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vitali.config import Config
from vitali.data.expenses import build_expense_profile, load_expense_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/base.yaml",
        help="Path to the base YAML configuration.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/expense_profile.json",
        help="Where to write the expense profile JSON.",
    )
    parser.add_argument(
        "--input",
        dest="input_files",
        action="append",
        help="Optional workbook path. Repeat the flag to pass multiple files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Config.from_yaml(args.config)

    source_files = args.input_files or config.expense_data.source_files
    dataset = load_expense_data(source_files, config.expense_data)
    profile = build_expense_profile(dataset.records)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(profile, indent=2, ensure_ascii=True), encoding="utf-8")


if __name__ == "__main__":
    main()
