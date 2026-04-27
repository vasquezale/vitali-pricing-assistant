"""Build a reservation-level analysis table from the anonymized income extract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vitali.config import Config
from vitali.data.income import build_income_analysis_table, load_income_data, resolve_fx_rates


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml", help="Path to project YAML configuration.")
    parser.add_argument("--input", default=None, help="Optional override for the anonymized income CSV path.")
    parser.add_argument(
        "--output",
        default="artifacts/income_analysis_table.csv",
        help="Where to write the reservation-level analysis table.",
    )
    parser.add_argument(
        "--fx-rates-json",
        default=None,
        help="Optional JSON object with currency-to-CRC rates, e.g. '{\"USD\":510.0,\"CRC\":1.0}'. Overrides config.",
    )
    return parser.parse_args()


def main() -> None:
    """Load, validate, enrich, and export the income analysis table."""
    args = parse_args()
    config = Config.from_yaml(args.config)
    input_path = args.input or config.income_data.source_file
    dataset = load_income_data(input_path, config.income_data)
    fx_rates = json.loads(args.fx_rates_json) if args.fx_rates_json else resolve_fx_rates(config.fx_normalization)

    table = build_income_analysis_table(dataset.records, fx_rates_to_crc=fx_rates)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_path, index=False)

    preview = {
        "rows": int(len(table)),
        "currencies": sorted(table["currency"].dropna().unique().tolist()),
        "fx_normalization_status": table["fx_normalization_status"].value_counts(dropna=False).to_dict(),
        "fx_rates_to_crc": fx_rates,
        "output": str(output_path),
    }
    print(json.dumps(preview, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
