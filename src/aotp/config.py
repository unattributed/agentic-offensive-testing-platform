"""Fail-closed YAML configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when configuration is absent, malformed, or incomplete."""


@dataclass(frozen=True)
class LoadedConfig:
    path: Path
    data: dict[str, Any]


def load_yaml(path: str | Path) -> LoadedConfig:
    config_path = Path(path).expanduser().resolve()
    if not config_path.is_file():
        raise ConfigError(f"configuration file does not exist: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"configuration could not be loaded: {config_path}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be a mapping")
    return LoadedConfig(config_path, raw)


def require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{field} must be a mapping")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigError(f"{field} must be a list")
    return value


def require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{field} must be non-empty text")
    return value.strip()


def validate_scope_shape(scope: dict[str, Any]) -> None:
    require_text(scope.get("schema_version"), "schema_version")
    require_text(scope.get("scope_id"), "scope_id")
    require_text(scope.get("sponsor_alias"), "sponsor_alias")
    require_mapping(scope.get("authorization"), "authorization")
    require_mapping(scope.get("rules_of_engagement"), "rules_of_engagement")
    require_list(scope.get("allowed_targets"), "allowed_targets")
    require_list(scope.get("allowed_categories"), "allowed_categories")
    require_list(scope.get("forbidden_actions"), "forbidden_actions")
    require_mapping(scope.get("rate_limits"), "rate_limits")
    evidence = require_mapping(scope.get("evidence"), "evidence")
    require_text(evidence.get("workspace"), "evidence.workspace")
    require_text(evidence.get("handling"), "evidence.handling")
