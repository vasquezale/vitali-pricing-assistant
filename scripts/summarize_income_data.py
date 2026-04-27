"""Generate a reproducible analytical summary of the anonymized income extract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vitali.config import Config
from vitali.data.income import build_income_summary, load_income_data, render_income_summary_markdown


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml", help="Path to project YAML configuration.")
    parser.add_argument("--input", default=None, help="Optional override for the anonymized income CSV path.")
    parser.add_argument(
        "--json-output",
        default="artifacts/income_summary.json",
        help="Where to write the machine-readable summary.",
    )
    parser.add_argument(
        "--markdown-output",
        default="artifacts/income_summary.md",
        help="Where to write the Markdown summary.",
    )
    return parser.parse_args()


def main() -> None:
    """Load, validate, summarize, and export the anonymized income dataset."""
    args = parse_args()
    config = Config.from_yaml(args.config)
    input_path = args.input or config.income_data.source_file
    dataset = load_income_data(input_path, config.income_data)
    summary = build_income_summary(dataset.records)

    json_output = Path(args.json_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    markdown_output = Path(args.markdown_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(
        render_income_summary_markdown(summary, dataset.source_path.name),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
