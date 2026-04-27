"""Centralized configuration loaded from YAML."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PathsConfig:
    """Project directory paths."""

    raw: str = "data/raw"
    sanitized: str = "data/sanitized"
    interim: str = "data/interim"
    processed: str = "data/processed"
    external: str = "data/external"
    artifacts: str = "artifacts"


@dataclass
class ModelingConfig:
    """Modeling hyperparameters and evaluation settings."""

    test_window_months: int = 1
    min_train_months: int = 6
    confidence_level: float = 0.95


@dataclass
class IncomeDataConfig:
    """Income extract settings for reproducible exploratory analysis."""

    source_file: str = "data/external/DatosVitali_ingresos_anonimizados.csv"
    date_columns: list[str] = field(
        default_factory=lambda: ["movement_date", "booking_date", "check_in", "check_out"]
    )
    required_columns: list[str] = field(
        default_factory=lambda: [
            "record_type",
            "movement_date",
            "booking_date",
            "check_in",
            "check_out",
            "nights",
            "unit_id",
            "currency",
            "net_amount",
            "service_fee",
            "cleaning_fee",
            "gross_income",
            "booking_lead_days",
        ]
    )
    allowed_record_types: list[str] = field(default_factory=lambda: ["reservation", "resolution_payment"])
    allowed_currencies: list[str] = field(default_factory=lambda: ["USD", "CRC"])


@dataclass
class ExpenseDataConfig:
    """Expense workbook settings for reproducible financial ingestion."""

    source_files: list[str] = field(
        default_factory=lambda: [
            "data/raw/financials/FINCA VITALI _ Contabilidad Administrativa _ 2025.xlsx",
            "data/raw/financials/FINCA VITALI _ Contabilidad Administrativa _ 2026.xlsx",
        ]
    )
    expected_sheet_names_by_file: dict[str, list[str]] = field(
        default_factory=lambda: {
            "FINCA VITALI _ Contabilidad Administrativa _ 2025.xlsx": [
                "ENERO",
                "FEBRERO",
                "MARZO",
                "ABRIL",
                "MAYO",
                "JUNIO",
                "JULIO",
                "AGOSTO",
                "SEPTIEMBRE",
                "OCTUBRE",
                "NOVIEMBRE",
                "DICIEMBRE",
            ],
            "FINCA VITALI _ Contabilidad Administrativa _ 2026.xlsx": ["ENERO", "FEBRERO", "MARZO"],
        }
    )


@dataclass
class FxNormalizationConfig:
    """Explicit foreign-exchange normalization policy for income analysis."""

    enabled: bool = False
    strategy: str = "preserve_original"
    target_currency: str = "CRC"
    rates_to_crc: dict[str, float] = field(default_factory=dict)


@dataclass
class Config:
    """Top-level project configuration."""

    project_name: str = "proyecto-vitali"
    version: str = "0.1.0"
    seed: int = 42
    paths: PathsConfig = field(default_factory=PathsConfig)
    modeling: ModelingConfig = field(default_factory=ModelingConfig)
    income_data: IncomeDataConfig = field(default_factory=IncomeDataConfig)
    expense_data: ExpenseDataConfig = field(default_factory=ExpenseDataConfig)
    fx_normalization: FxNormalizationConfig = field(default_factory=FxNormalizationConfig)

    @classmethod
    def from_yaml(cls, path: str | Path = "configs/base.yaml") -> "Config":
        """Load configuration from a YAML file."""
        with open(path, encoding="utf-8") as f:
            raw: dict[str, Any] = yaml.safe_load(f) or {}

        paths = PathsConfig(**raw.get("paths", {}))
        modeling = ModelingConfig(**raw.get("modeling", {}))
        income_data = IncomeDataConfig(**raw.get("income_data", {}))
        expense_data = ExpenseDataConfig(**raw.get("expense_data", {}))
        fx_normalization = FxNormalizationConfig(**raw.get("fx_normalization", {}))
        project = raw.get("project", {})

        return cls(
            project_name=project.get("name", cls.project_name),
            version=project.get("version", cls.version),
            seed=project.get("seed", cls.seed),
            paths=paths,
            modeling=modeling,
            income_data=income_data,
            expense_data=expense_data,
            fx_normalization=fx_normalization,
        )
