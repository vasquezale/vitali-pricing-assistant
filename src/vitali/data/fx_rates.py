"""Load and validate FX rates used for the canonical FX income table.

This module does not decide *which* FX rates are correct. It only formalizes:
- how rates are supplied (file / config / CLI)
- how they are validated (positive floats; CRC defaults to 1.0)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_fx_rates_to_crc(path: str | Path) -> dict[str, float]:
    """Load a mapping of currency -> rate_to_crc from JSON or YAML."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"FX rates file not found: {p}")

    if p.suffix.lower() in {".yml", ".yaml"}:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    elif p.suffix.lower() == ".json":
        raw = json.loads(p.read_text(encoding="utf-8")) or {}
    else:
        raise ValueError(f"Unsupported FX rates file extension: {p.suffix}")

    if not isinstance(raw, dict):
        raise ValueError("FX rates file must contain an object/dict mapping currency to numeric rate.")

    rates: dict[str, float] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not k.strip():
            raise ValueError("FX rate currency codes must be non-empty strings.")
        rates[k.strip().upper()] = _to_positive_float(v, key=k)

    return validate_fx_rates_to_crc(rates)


def resolve_fx_rates_to_crc(
    *,
    fx_rates_json: str | None,
    fx_rates_file: str | Path | None,
    config_rates_to_crc: dict[str, Any] | None,
) -> dict[str, float]:
    """Resolve FX rates from (1) JSON string, (2) file, (3) config mapping.

    This function does not choose values; it only resolves and validates inputs.
    """
    if fx_rates_json:
        return validate_fx_rates_to_crc(json.loads(fx_rates_json))

    if fx_rates_file:
        p = Path(fx_rates_file)
        if p.is_file():
            return load_fx_rates_to_crc(p)

    if config_rates_to_crc:
        return validate_fx_rates_to_crc(config_rates_to_crc)

    raise ValueError("No FX rates source available.")


def validate_fx_rates_to_crc(rates_to_crc: dict[str, Any]) -> dict[str, float]:
    """Validate and normalize FX rates mapping."""
    if not isinstance(rates_to_crc, dict) or not rates_to_crc:
        raise ValueError("FX rates mapping is empty.")

    out: dict[str, float] = {}
    for k, v in rates_to_crc.items():
        if not isinstance(k, str) or not k.strip():
            raise ValueError("FX rate currency codes must be non-empty strings.")
        out[k.strip().upper()] = _to_positive_float(v, key=k)

    if "CRC" not in out:
        out["CRC"] = 1.0

    return out


def _to_positive_float(value: Any, *, key: str) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"FX rate for {key} must be numeric.") from exc
    if f <= 0:
        raise ValueError(f"FX rate for {key} must be > 0.")
    return f

