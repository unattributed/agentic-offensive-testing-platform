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


SUPPORTED_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class TargetScope:
    alias: str
    domains: tuple[str, ...]
    services: tuple[str, ...]
    apis: tuple[str, ...]
    environments: tuple[str, ...]
    approved_account_aliases: tuple[str, ...]


@dataclass(frozen=True)
class ScopeConfig:
    schema_version: str
    scope_id: str
    program_alias: str
    sponsor_alias: str
    operator_alias: str
    targets: tuple[TargetScope, ...]
    allowed_categories: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    data: dict[str, Any]

    def target(self, alias: str) -> TargetScope | None:
        return next((target for target in self.targets if target.alias == alias), None)


@dataclass(frozen=True)
class ProgramProfile:
    schema_version: str
    program_alias: str
    in_scope_asset_aliases: tuple[str, ...]
    out_of_scope_asset_aliases: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    allowed_testing_categories: tuple[str, ...]
    forbidden_testing_categories: tuple[str, ...]
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


def require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{field} must be true or false")
    return value


def require_positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{field} must be a positive integer")
    return value


def require_text_list(value: Any, field: str, *, allow_empty: bool = True) -> list[str]:
    values = require_list(value, field)
    if not allow_empty and not values:
        raise ConfigError(f"{field} must not be empty")
    return [require_text(item, f"{field}[{index}]") for index, item in enumerate(values)]


def _reject_unknown(mapping: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ConfigError(f"{field} contains unknown fields: {', '.join(unknown)}")


def _validate_unique(values: list[str], field: str) -> None:
    if len(values) != len(set(values)):
        raise ConfigError(f"{field} must not contain duplicates")


def parse_scope(scope: dict[str, Any]) -> ScopeConfig:
    _reject_unknown(
        scope,
        {
            "schema_version",
            "scope_id",
            "program_alias",
            "sponsor_alias",
            "operator_alias",
            "authorization",
            "rules_of_engagement",
            "allowed_targets",
            "allowed_test_windows",
            "allowed_categories",
            "forbidden_actions",
            "rate_limits",
            "fuzzing",
            "service_control_panels",
            "cryptographic_controls",
            "provided_artifacts",
            "evidence",
            "reporting",
            "stop_conditions",
            "operator_approval",
        },
        "scope",
    )
    schema_version = require_text(scope.get("schema_version"), "schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ConfigError(f"unsupported schema_version: {schema_version}")
    scope_id = require_text(scope.get("scope_id"), "scope_id")
    program_alias = require_text(scope.get("program_alias"), "program_alias")
    sponsor_alias = require_text(scope.get("sponsor_alias"), "sponsor_alias")
    operator_alias = require_text(scope.get("operator_alias"), "operator_alias")
    require_mapping(scope.get("authorization"), "authorization")
    require_mapping(scope.get("rules_of_engagement"), "rules_of_engagement")
    raw_targets = require_list(scope.get("allowed_targets"), "allowed_targets")
    targets: list[TargetScope] = []
    for index, raw_target in enumerate(raw_targets):
        field = f"allowed_targets[{index}]"
        target = require_mapping(raw_target, field)
        _reject_unknown(
            target,
            {"alias", "domains", "services", "apis", "environments", "approved_account_aliases"},
            field,
        )
        targets.append(
            TargetScope(
                alias=require_text(target.get("alias"), f"{field}.alias"),
                domains=tuple(require_text_list(target.get("domains"), f"{field}.domains")),
                services=tuple(require_text_list(target.get("services"), f"{field}.services")),
                apis=tuple(require_text_list(target.get("apis"), f"{field}.apis")),
                environments=tuple(require_text_list(target.get("environments"), f"{field}.environments")),
                approved_account_aliases=tuple(
                    require_text_list(target.get("approved_account_aliases"), f"{field}.approved_account_aliases")
                ),
            )
        )
    target_aliases = [target.alias for target in targets]
    _validate_unique(target_aliases, "allowed_targets aliases")
    allowed_categories = require_text_list(scope.get("allowed_categories"), "allowed_categories", allow_empty=False)
    forbidden_actions = require_text_list(scope.get("forbidden_actions"), "forbidden_actions", allow_empty=False)
    _validate_unique(allowed_categories, "allowed_categories")
    _validate_unique(forbidden_actions, "forbidden_actions")
    rate_limits = require_mapping(scope.get("rate_limits"), "rate_limits")
    require_positive_int(rate_limits.get("requests_per_minute"), "rate_limits.requests_per_minute")
    require_positive_int(rate_limits.get("max_requests"), "rate_limits.max_requests")
    require_list(scope.get("allowed_test_windows"), "allowed_test_windows")
    require_list(scope.get("provided_artifacts"), "provided_artifacts")
    require_list(scope.get("stop_conditions"), "stop_conditions")
    evidence = require_mapping(scope.get("evidence"), "evidence")
    require_text(evidence.get("workspace"), "evidence.workspace")
    require_text(evidence.get("handling"), "evidence.handling")
    return ScopeConfig(
        schema_version=schema_version,
        scope_id=scope_id,
        program_alias=program_alias,
        sponsor_alias=sponsor_alias,
        operator_alias=operator_alias,
        targets=tuple(targets),
        allowed_categories=tuple(allowed_categories),
        forbidden_actions=tuple(forbidden_actions),
        data=scope,
    )


def validate_scope_shape(scope: dict[str, Any]) -> None:
    parse_scope(scope)


def parse_program_profile(profile: dict[str, Any]) -> ProgramProfile:
    _reject_unknown(
        profile,
        {
            "schema_version",
            "program_alias",
            "platform_reference",
            "accepted_policy_date",
            "authorization_reference",
            "safe_harbor_reference",
            "confidentiality_reference",
            "in_scope_asset_aliases",
            "out_of_scope_asset_aliases",
            "prohibited_actions",
            "rate_limits",
            "allowed_testing_categories",
            "forbidden_testing_categories",
            "report_format_expectations",
            "disclosure_rules",
            "emergency_stop_condition",
            "sensitive_workflow_notes",
        },
        "program profile",
    )
    schema_version = require_text(profile.get("schema_version"), "schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ConfigError(f"unsupported schema_version: {schema_version}")
    program_alias = require_text(profile.get("program_alias"), "program_alias")
    for field in (
        "platform_reference",
        "accepted_policy_date",
        "authorization_reference",
        "safe_harbor_reference",
        "confidentiality_reference",
        "report_format_expectations",
        "disclosure_rules",
        "emergency_stop_condition",
        "sensitive_workflow_notes",
    ):
        require_text(profile.get(field), field)
    rate_limits = require_mapping(profile.get("rate_limits"), "rate_limits")
    require_positive_int(rate_limits.get("requests_per_minute"), "rate_limits.requests_per_minute")
    in_scope = require_text_list(profile.get("in_scope_asset_aliases"), "in_scope_asset_aliases", allow_empty=False)
    out_of_scope = require_text_list(profile.get("out_of_scope_asset_aliases"), "out_of_scope_asset_aliases")
    prohibited = require_text_list(profile.get("prohibited_actions"), "prohibited_actions", allow_empty=False)
    allowed = require_text_list(
        profile.get("allowed_testing_categories"), "allowed_testing_categories", allow_empty=False
    )
    forbidden = require_text_list(profile.get("forbidden_testing_categories"), "forbidden_testing_categories")
    for values, field in (
        (in_scope, "in_scope_asset_aliases"),
        (out_of_scope, "out_of_scope_asset_aliases"),
        (prohibited, "prohibited_actions"),
        (allowed, "allowed_testing_categories"),
        (forbidden, "forbidden_testing_categories"),
    ):
        _validate_unique(values, field)
    overlap = set(in_scope) & set(out_of_scope)
    if overlap:
        raise ConfigError(f"asset aliases cannot be both in and out of scope: {', '.join(sorted(overlap))}")
    category_overlap = set(allowed) & set(forbidden)
    if category_overlap:
        raise ConfigError(
            f"testing categories cannot be both allowed and forbidden: {', '.join(sorted(category_overlap))}"
        )
    return ProgramProfile(
        schema_version=schema_version,
        program_alias=program_alias,
        in_scope_asset_aliases=tuple(in_scope),
        out_of_scope_asset_aliases=tuple(out_of_scope),
        prohibited_actions=tuple(prohibited),
        allowed_testing_categories=tuple(allowed),
        forbidden_testing_categories=tuple(forbidden),
        data=profile,
    )
