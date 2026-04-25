"""Centralized configuration loaded from YAML."""

from dataclasses import dataclass, field
from pathlib import Path

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
class Config:
    """Top-level project configuration."""

    project_name: str = "proyecto-vitali"
    version: str = "0.1.0"
    seed: int = 42
    paths: PathsConfig = field(default_factory=PathsConfig)
    modeling: ModelingConfig = field(default_factory=ModelingConfig)

    @classmethod
    def from_yaml(cls, path: str | Path = "configs/base.yaml") -> "Config":
        """Load configuration from a YAML file."""
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        paths = PathsConfig(**raw.get("paths", {}))
        modeling = ModelingConfig(**raw.get("modeling", {}))
        project = raw.get("project", {})

        return cls(
            project_name=project.get("name", cls.project_name),
            version=project.get("version", cls.version),
            seed=project.get("seed", cls.seed),
            paths=paths,
            modeling=modeling,
        )
