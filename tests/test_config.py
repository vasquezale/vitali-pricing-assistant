"""Tests for configuration loading."""

from vitali.config import Config, IncomeDataConfig, ModelingConfig, PathsConfig


def test_config_from_yaml(config: Config) -> None:
    assert config.project_name == "proyecto-vitali"
    assert config.seed == 42
    assert isinstance(config.paths, PathsConfig)
    assert isinstance(config.modeling, ModelingConfig)
    assert isinstance(config.income_data, IncomeDataConfig)


def test_config_defaults() -> None:
    cfg = Config()
    assert cfg.seed == 42
    assert cfg.paths.raw == "data/raw"
    assert cfg.modeling.confidence_level == 0.95
    assert cfg.income_data.allowed_currencies == ["USD", "CRC"]
