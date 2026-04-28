"""Build the canonical FX-normalized income table (Yellow gate).

This script formalizes the producer of:
    artifacts/income_analysis_table_fx.csv

Constraints:
- Does not rename the canonical artifact.
- Does not invent FX policy: requires explicit rates via CLI or config.
- Uses existing transformation logic in `vitali.data.income.build_income_analysis_table`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from vitali.config import Config
from vitali.contracts.artifacts import ARTIFACTS, REQUIRED_INCOME_FX_COLUMNS
from vitali.data.fx_rates import resolve_fx_rates_to_crc, validate_fx_rates_to_crc
from vitali.data.fx_table import build_income_analysis_table_fx
from vitali.data.income import resolve_fx_rates


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml", help="Path to project YAML configuration.")
    parser.add_argument("--input", default=None, help="Optional override for the anonymized income CSV path.")
    parser.add_argument(
        "--fx-rates-json",
        default=None,
        help="Required JSON object with currency-to-CRC rates, e.g. '{\"USD\":510.0,\"CRC\":1.0}'. "
        "Overrides other sources.",
    )
    parser.add_argument(
        "--fx-rates-file",
        default="configs/fx_rates_to_crc.json",
        help="Path to FX rates file (JSON/YAML). Default: configs/fx_rates_to_crc.json "
        "(typically local; see configs/fx_rates_to_crc.example.json).",
    )
    parser.add_argument(
        "--output",
        default=str(ARTIFACTS.income_analysis_table_fx_csv),
        help="Output path (default: canonical artifacts/income_analysis_table_fx.csv).",
    )
    return parser.parse_args()


def resolve_fx_rates_for_fx_table(args: argparse.Namespace, config: Config) -> dict[str, float]:
    """Resolve FX rates using (1) CLI JSON, (2) rates file, (3) config manual_static."""
    fx_rates = resolve_fx_rates(config.fx_normalization)
    try:
        return resolve_fx_rates_to_crc(
            fx_rates_json=args.fx_rates_json,
            fx_rates_file=args.fx_rates_file,
            config_rates_to_crc=dict(fx_rates) if fx_rates else None,
        )
    except ValueError as exc:
        raise SystemExit(
            "FX rates are required to produce artifacts/income_analysis_table_fx.csv.\n"
            "- Provide --fx-rates-json, OR\n"
            "- Create configs/fx_rates_to_crc.json (see configs/fx_rates_to_crc.example.json), OR\n"
            "- Set fx_normalization.enabled=true and strategy=manual_static in config with rates_to_crc."
        ) from exc


def main() -> int:
    args = _parse_args()
    config = Config.from_yaml(args.config)
    repo_root = Path.cwd().resolve()

    input_path = args.input or config.income_data.source_file

    fx_rates = resolve_fx_rates_for_fx_table(args, config)

    out = build_income_analysis_table_fx(
        repo_root=repo_root,
        input_csv=input_path,
        config=config,
        fx_rates_to_crc=dict(fx_rates),
        output_csv=args.output,
    )

    preview = {
        "output": str(out),
        "required_columns": REQUIRED_INCOME_FX_COLUMNS,
        "fx_rates_to_crc": fx_rates,
    }
    print(json.dumps(preview, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

