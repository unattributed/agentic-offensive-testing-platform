"""Campaign file loading."""

from __future__ import annotations

from typing import Any

from .config import ConfigError, LoadedConfig, load_yaml, require_list, require_text


def load_campaign(path: str) -> LoadedConfig:
    loaded = load_yaml(path)
    require_text(loaded.data.get("campaign_id"), "campaign_id")
    require_text(loaded.data.get("name"), "name")
    objectives = require_list(loaded.data.get("objectives"), "objectives")
    if not objectives or not all(isinstance(item, dict) for item in objectives):
        raise ConfigError("campaign objectives must be a non-empty list of mappings")
    return loaded


def objective_ids(campaign: dict[str, Any]) -> list[str]:
    return [str(item.get("id")) for item in campaign["objectives"]]
