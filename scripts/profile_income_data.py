"""Generate a reproducible profile of the anonymized income extract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vitali.config import Config
from vitali.data.income import build_income_profile, load_income_data


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/base.yaml",
        help="Path to project YAML configuration.",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Optional override for the anonymized income CSV path.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/income_profile.json",
        help="Where to write the generated JSON profile.",
    )
    return parser.parse_args()


def main() -> None:
    """Load, validate, and profile the income dataset."""
    args = parse_args()
    config = Config.from_yaml(args.config)
    input_path = args.input or config.income_data.source_file
    dataset = load_income_data(input_path, config.income_data)
    profile = build_income_profile(dataset.records)
    profile["source_name"] = dataset.source_path.name

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(profile, indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps(profile, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
