"""Canonical artifact paths and minimal schemas (Yellow gate).

This module centralizes *existing* contracts:
- canonical relative paths under repo root
- minimal required columns for key CSV/parquet artifacts

It must not rename outputs nor change their meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CanonicalArtifacts:
    """Canonical relative paths under the repo root."""

    # Phase 2/3 shared FX table (critical consumer contract)
    income_analysis_table_fx_csv: Path = Path("artifacts/income_analysis_table_fx.csv")

    # Phase 3 lanes (sanitized vs interim)
    income_reservations_fx_crc_sanitized_parquet: Path = Path(
        "data/sanitized/income_reservations_fx_crc_sanitized.parquet"
    )
    income_reservations_fx_crc_interim_parquet: Path = Path(
        "data/interim/income_reservations_fx_crc_interim.parquet"
    )

    # Phase 5/6 evidence artifacts
    phase5_metrics_json: Path = Path("artifacts/baseline/phase5_metrics.json")
    phase6_rolling_metrics_json: Path = Path("artifacts/evaluation/phase6_rolling_metrics.json")

    def resolve(self, repo_root: str | Path) -> "ResolvedCanonicalArtifacts":
        root = Path(repo_root).resolve()
        return ResolvedCanonicalArtifacts(
            income_analysis_table_fx_csv=root / self.income_analysis_table_fx_csv,
            income_reservations_fx_crc_sanitized_parquet=root / self.income_reservations_fx_crc_sanitized_parquet,
            income_reservations_fx_crc_interim_parquet=root / self.income_reservations_fx_crc_interim_parquet,
            phase5_metrics_json=root / self.phase5_metrics_json,
            phase6_rolling_metrics_json=root / self.phase6_rolling_metrics_json,
        )


@dataclass(frozen=True)
class ResolvedCanonicalArtifacts:
    """Absolute paths to canonical artifacts for a specific repo root."""

    income_analysis_table_fx_csv: Path
    income_reservations_fx_crc_sanitized_parquet: Path
    income_reservations_fx_crc_interim_parquet: Path
    phase5_metrics_json: Path
    phase6_rolling_metrics_json: Path


ARTIFACTS = CanonicalArtifacts()


# --- Minimal schema contracts (do not expand without evidence) ---

# This CSV is consumed by Phase 2 monthly pipeline and Phase 3 join logic.
REQUIRED_INCOME_FX_COLUMNS = [
    "check_in",
    "gross_income_crc",
    "net_amount_crc",
    "unit_id",
    "currency",
]

