"""Generate aggregated income summaries with currency as a mandatory grouping axis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vitali.config import Config
from vitali.data.income import (
    build_income_analysis_table,
    build_income_segment_summary,
    load_income_data,
    render_income_segment_summary_markdown,
    resolve_fx_rates,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml", help="Path to project YAML configuration.")
    parser.add_argument("--input", default=None, help="Optional override for the anonymized income CSV path.")
    parser.add_argument(
        "--json-output",
        default="artifacts/income_segment_summary.json",
        help="Where to write the machine-readable segment summary.",
    )
    parser.add_argument(
        "--markdown-output",
        default="artifacts/income_segment_summary.md",
        help="Where to write the Markdown segment summary.",
    )
    parser.add_argument(
        "--fx-rates-json",
        default=None,
        help="Optional JSON object with currency-to-CRC rates, e.g. '{\"USD\":510.0,\"CRC\":1.0}'. Overrides config.",
    )
    return parser.parse_args()


def main() -> None:
    """Load income data, derive an analysis table, and aggregate it by safe segments."""
    args = parse_args()
    config = Config.from_yaml(args.config)
    input_path = args.input or config.income_data.source_file
    dataset = load_income_data(input_path, config.income_data)
    fx_rates = json.loads(args.fx_rates_json) if args.fx_rates_json else resolve_fx_rates(config.fx_normalization)

    analysis_table = build_income_analysis_table(dataset.records, fx_rates_to_crc=fx_rates)
    summary = build_income_segment_summary(analysis_table)

    json_output = Path(args.json_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    markdown_output = Path(args.markdown_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(
        render_income_segment_summary_markdown(summary, dataset.source_path.name),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
