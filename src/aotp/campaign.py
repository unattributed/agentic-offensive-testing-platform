"""Strict campaign parsing and objective graph validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import (
    ConfigError,
    LoadedConfig,
    load_yaml,
    require_bool,
    require_list,
    require_mapping,
    require_positive_int,
    require_text,
    require_text_list,
)


SUPPORTED_MODULES = {
    "wstg_webapp",
    "service_control_panel",
    "bounded_fuzzing",
    "sbom_review",
    "crypto_controls",
}

SUPPORTED_STOP_CONDITIONS = {
    "operator_stop",
    "policy_denial",
    "human_review",
    "rate_limit",
    "iteration_limit",
    "runtime_limit",
    "request_limit",
    "target_instability",
    "authentication_lockout_risk",
    "redaction_failure",
}


@dataclass(frozen=True)
class CampaignLimits:
    max_iterations: int
    max_runtime_seconds: int
    max_requests: int
    max_consecutive_failures: int


@dataclass(frozen=True)
class CampaignObjective:
    objective_id: str
    title: str
    module: str
    category: str
    action: str
    target_alias: str
    priority: int
    depends_on: tuple[str, ...]
    requires_human_approval: bool
    data: dict[str, Any]


@dataclass(frozen=True)
class CampaignDefinition:
    campaign_id: str
    name: str
    description: str
    limits: CampaignLimits
    stop_conditions: tuple[str, ...]
    objectives: tuple[CampaignObjective, ...]
    data: dict[str, Any]


def _reject_unknown(mapping: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ConfigError(f"{field} contains unknown fields: {', '.join(unknown)}")


def _validate_dependency_graph(objectives: list[CampaignObjective]) -> None:
    by_id = {objective.objective_id: objective for objective in objectives}
    for objective in objectives:
        unknown = sorted(set(objective.depends_on) - set(by_id))
        if unknown:
            raise ConfigError(
                f"objective {objective.objective_id} has unknown dependencies: {', '.join(unknown)}"
            )
        if objective.objective_id in objective.depends_on:
            raise ConfigError(f"objective {objective.objective_id} cannot depend on itself")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(objective_id: str) -> None:
        if objective_id in visiting:
            raise ConfigError(f"campaign objective dependency cycle includes: {objective_id}")
        if objective_id in visited:
            return
        visiting.add(objective_id)
        for dependency in by_id[objective_id].depends_on:
            visit(dependency)
        visiting.remove(objective_id)
        visited.add(objective_id)

    for objective_id in by_id:
        visit(objective_id)


def parse_campaign(data: dict[str, Any]) -> CampaignDefinition:
    _reject_unknown(
        data,
        {
            "schema_version",
            "campaign_id",
            "name",
            "description",
            "limits",
            "execution",
            "stop_conditions",
            "objectives",
        },
        "campaign",
    )
    schema_version = require_text(data.get("schema_version"), "schema_version")
    if schema_version != "1.0":
        raise ConfigError(f"unsupported campaign schema_version: {schema_version}")
    campaign_id = require_text(data.get("campaign_id"), "campaign_id")
    name = require_text(data.get("name"), "name")
    description = require_text(data.get("description"), "description")

    raw_limits = require_mapping(data.get("limits"), "limits")
    _reject_unknown(
        raw_limits,
        {"max_iterations", "max_runtime_seconds", "max_requests", "max_consecutive_failures"},
        "limits",
    )
    limits = CampaignLimits(
        max_iterations=require_positive_int(raw_limits.get("max_iterations"), "limits.max_iterations"),
        max_runtime_seconds=require_positive_int(
            raw_limits.get("max_runtime_seconds"), "limits.max_runtime_seconds"
        ),
        max_requests=require_positive_int(raw_limits.get("max_requests"), "limits.max_requests"),
        max_consecutive_failures=require_positive_int(
            raw_limits.get("max_consecutive_failures"), "limits.max_consecutive_failures"
        ),
    )

    execution = require_mapping(data.get("execution"), "execution")
    _reject_unknown(
        execution,
        {
            "default_mode",
            "continue_on_inconclusive",
            "pause_on_manual_review",
            "stop_on_policy_denial",
        },
        "execution",
    )
    if require_text(execution.get("default_mode"), "execution.default_mode") != "dry_run":
        raise ConfigError("campaign execution.default_mode must be dry_run")
    for field in ("continue_on_inconclusive", "pause_on_manual_review", "stop_on_policy_denial"):
        require_bool(execution.get(field), f"execution.{field}")
    if not execution["pause_on_manual_review"] or not execution["stop_on_policy_denial"]:
        raise ConfigError("campaigns must pause on manual review and stop on policy denial")

    stop_conditions = require_text_list(
        data.get("stop_conditions"), "stop_conditions", allow_empty=False
    )
    if len(stop_conditions) != len(set(stop_conditions)):
        raise ConfigError("stop_conditions must not contain duplicates")
    unsupported_stops = sorted(set(stop_conditions) - SUPPORTED_STOP_CONDITIONS)
    if unsupported_stops:
        raise ConfigError(f"unsupported campaign stop conditions: {', '.join(unsupported_stops)}")
    mandatory_stops = {"operator_stop", "policy_denial", "human_review"}
    missing_stops = sorted(mandatory_stops - set(stop_conditions))
    if missing_stops:
        raise ConfigError(f"campaign is missing mandatory stop conditions: {', '.join(missing_stops)}")

    raw_objectives = require_list(data.get("objectives"), "objectives")
    if not raw_objectives:
        raise ConfigError("campaign objectives must not be empty")
    objectives: list[CampaignObjective] = []
    allowed_objective_fields = {
        "id",
        "title",
        "module",
        "category",
        "action",
        "target_alias",
        "target_category",
        "domain",
        "service",
        "api",
        "environment",
        "account_alias",
        "artifact",
        "state_changing",
        "wstg_mapping",
        "artifact_mapping",
        "priority",
        "depends_on",
        "requires_human_approval",
        "parameters",
    }
    for index, raw_objective in enumerate(raw_objectives):
        field = f"objectives[{index}]"
        objective = require_mapping(raw_objective, field)
        _reject_unknown(objective, allowed_objective_fields, field)
        module = require_text(objective.get("module"), f"{field}.module")
        if module not in SUPPORTED_MODULES:
            raise ConfigError(f"{field}.module is unsupported: {module}")
        category = require_text(objective.get("category"), f"{field}.category")
        if category != module:
            raise ConfigError(f"{field}.category must match module")
        depends_on = require_text_list(objective.get("depends_on"), f"{field}.depends_on")
        if len(depends_on) != len(set(depends_on)):
            raise ConfigError(f"{field}.depends_on must not contain duplicates")
        require_mapping(objective.get("parameters"), f"{field}.parameters")
        if "wstg_mapping" in objective:
            require_text_list(objective["wstg_mapping"], f"{field}.wstg_mapping")
        if "artifact_mapping" in objective:
            require_text_list(objective["artifact_mapping"], f"{field}.artifact_mapping")
        objectives.append(
            CampaignObjective(
                objective_id=require_text(objective.get("id"), f"{field}.id"),
                title=require_text(objective.get("title"), f"{field}.title"),
                module=module,
                category=category,
                action=require_text(objective.get("action"), f"{field}.action"),
                target_alias=require_text(objective.get("target_alias"), f"{field}.target_alias"),
                priority=require_positive_int(objective.get("priority"), f"{field}.priority"),
                depends_on=tuple(depends_on),
                requires_human_approval=require_bool(
                    objective.get("requires_human_approval"),
                    f"{field}.requires_human_approval",
                ),
                data=objective,
            )
        )
    objective_ids = [objective.objective_id for objective in objectives]
    if len(objective_ids) != len(set(objective_ids)):
        raise ConfigError("campaign objective ids must not contain duplicates")
    _validate_dependency_graph(objectives)
    return CampaignDefinition(
        campaign_id=campaign_id,
        name=name,
        description=description,
        limits=limits,
        stop_conditions=tuple(stop_conditions),
        objectives=tuple(objectives),
        data=data,
    )


def load_campaign(path: str) -> LoadedConfig:
    loaded = load_yaml(path)
    parse_campaign(loaded.data)
    return loaded


def objective_ids(campaign: dict[str, Any]) -> list[str]:
    return [objective.objective_id for objective in parse_campaign(campaign).objectives]
