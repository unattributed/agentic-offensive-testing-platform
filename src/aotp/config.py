"""Fail-closed YAML configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .control_panel import PANEL_SAFE_ACTIONS, PANEL_TYPES, PANEL_UNSAFE_ACTIONS


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
class PanelScope:
    alias: str
    target_alias: str
    panel_type: str
    exposure: str
    approved_actions: tuple[str, ...]
    denied_actions: tuple[str, ...]


@dataclass(frozen=True)
class ScopeConfig:
    schema_version: str
    scope_id: str
    program_alias: str
    sponsor_alias: str
    operator_alias: str
    targets: tuple[TargetScope, ...]
    panels: tuple[PanelScope, ...]
    allowed_categories: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    data: dict[str, Any]

    def target(self, alias: str) -> TargetScope | None:
        return next((target for target in self.targets if target.alias == alias), None)

    def panel(self, alias: str) -> PanelScope | None:
        return next((panel for panel in self.panels if panel.alias == alias), None)


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


@dataclass(frozen=True)
class OperatorApproval:
    approval_id: str
    operator_alias: str
    decision: str
    approved_at_utc: str
    valid_until_utc: str
    scope_sha256: str
    authorization_reference: str
    objective_ids: tuple[str, ...]
    campaign_ids: tuple[str, ...]
    data: dict[str, Any]


@dataclass(frozen=True)
class ReviewDecision:
    decision_id: str
    campaign_id: str
    objective_id: str
    operator_alias: str
    decision: str
    decided_at_utc: str
    state_sha256: str
    reason: str
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
    roe = require_mapping(scope.get("rules_of_engagement"), "rules_of_engagement")
    _reject_unknown(
        roe,
        {
            "confirmed",
            "reference",
            "confirmed_at_utc",
            "policy_sha256",
            "prohibited_actions_acknowledged",
            "evidence_handling_confirmed",
            "emergency_contact_reference",
            "target_instability_stop",
            "authentication_lockout_stop",
        },
        "rules_of_engagement",
    )
    require_bool(roe.get("confirmed"), "rules_of_engagement.confirmed")
    require_text(roe.get("reference"), "rules_of_engagement.reference")
    require_text(roe.get("confirmed_at_utc"), "rules_of_engagement.confirmed_at_utc")
    require_text(roe.get("policy_sha256"), "rules_of_engagement.policy_sha256")
    for field in (
        "prohibited_actions_acknowledged",
        "evidence_handling_confirmed",
        "target_instability_stop",
        "authentication_lockout_stop",
    ):
        require_bool(roe.get(field), f"rules_of_engagement.{field}")
    require_text(roe.get("emergency_contact_reference"), "rules_of_engagement.emergency_contact_reference")
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

    raw_panel_config = require_mapping(scope.get("service_control_panels"), "service_control_panels")
    _reject_unknown(raw_panel_config, {"authorized", "panels"}, "service_control_panels")
    require_bool(raw_panel_config.get("authorized"), "service_control_panels.authorized")
    raw_panels = raw_panel_config.get("panels", [])
    raw_panels = require_list(raw_panels, "service_control_panels.panels")
    panels: list[PanelScope] = []
    for index, raw_panel in enumerate(raw_panels):
        field = f"service_control_panels.panels[{index}]"
        panel = require_mapping(raw_panel, field)
        _reject_unknown(
            panel,
            {"alias", "target_alias", "panel_type", "exposure", "approved_actions", "denied_actions"},
            field,
        )
        panel_type = require_text(panel.get("panel_type"), f"{field}.panel_type")
        if panel_type not in PANEL_TYPES:
            raise ConfigError(f"{field}.panel_type is unsupported panel_type: {panel_type}")
        panel_target_alias = require_text(panel.get("target_alias"), f"{field}.target_alias")
        if panel_target_alias not in target_aliases:
            raise ConfigError(f"{field}.target_alias must reference allowed_targets")
        approved_actions = require_text_list(
            panel.get("approved_actions"), f"{field}.approved_actions", allow_empty=False
        )
        denied_actions = require_text_list(
            panel.get("denied_actions"), f"{field}.denied_actions", allow_empty=False
        )
        _validate_unique(approved_actions, f"{field}.approved_actions")
        _validate_unique(denied_actions, f"{field}.denied_actions")
        unsupported_approved = sorted(set(approved_actions) - PANEL_SAFE_ACTIONS)
        if unsupported_approved:
            raise ConfigError(
                f"{field}.approved_actions contains unsupported actions: "
                + ", ".join(unsupported_approved)
            )
        overlap = sorted(set(approved_actions) & set(denied_actions))
        if overlap:
            raise ConfigError(
                f"{field}.approved_actions and denied_actions overlap: " + ", ".join(overlap)
            )
        missing_denials = sorted(PANEL_UNSAFE_ACTIONS - set(denied_actions))
        if missing_denials:
            raise ConfigError(
                f"{field}.denied_actions is missing required safety denials: "
                + ", ".join(missing_denials)
            )
        panels.append(
            PanelScope(
                alias=require_text(panel.get("alias"), f"{field}.alias"),
                target_alias=panel_target_alias,
                panel_type=panel_type,
                exposure=require_text(panel.get("exposure"), f"{field}.exposure"),
                approved_actions=tuple(approved_actions),
                denied_actions=tuple(denied_actions),
            )
        )
    _validate_unique([panel.alias for panel in panels], "service_control_panels panel aliases")

    allowed_categories = require_text_list(scope.get("allowed_categories"), "allowed_categories", allow_empty=False)
    forbidden_actions = require_text_list(scope.get("forbidden_actions"), "forbidden_actions", allow_empty=False)
    _validate_unique(allowed_categories, "allowed_categories")
    _validate_unique(forbidden_actions, "forbidden_actions")
    rate_limits = require_mapping(scope.get("rate_limits"), "rate_limits")
    require_positive_int(rate_limits.get("requests_per_minute"), "rate_limits.requests_per_minute")
    require_positive_int(rate_limits.get("max_requests"), "rate_limits.max_requests")
    windows = require_list(scope.get("allowed_test_windows"), "allowed_test_windows")
    for index, raw_window in enumerate(windows):
        field = f"allowed_test_windows[{index}]"
        window = require_mapping(raw_window, field)
        _reject_unknown(window, {"label", "start_utc", "end_utc"}, field)
        require_text(window.get("label"), f"{field}.label")
        require_text(window.get("start_utc"), f"{field}.start_utc")
        require_text(window.get("end_utc"), f"{field}.end_utc")
    require_list(scope.get("provided_artifacts"), "provided_artifacts")
    require_list(scope.get("stop_conditions"), "stop_conditions")
    evidence = require_mapping(scope.get("evidence"), "evidence")
    _reject_unknown(
        evidence,
        {"workspace", "handling", "retention_days", "encryption_required", "allowed_artifact_types"},
        "evidence",
    )
    require_text(evidence.get("workspace"), "evidence.workspace")
    require_text(evidence.get("handling"), "evidence.handling")
    require_positive_int(evidence.get("retention_days"), "evidence.retention_days")
    require_bool(evidence.get("encryption_required"), "evidence.encryption_required")
    require_text_list(evidence.get("allowed_artifact_types"), "evidence.allowed_artifact_types", allow_empty=False)
    reporting = require_mapping(scope.get("reporting"), "reporting")
    _reject_unknown(
        reporting,
        {"disclosure_rules", "human_review_required", "automatic_submission"},
        "reporting",
    )
    require_text(reporting.get("disclosure_rules"), "reporting.disclosure_rules")
    require_bool(reporting.get("human_review_required"), "reporting.human_review_required")
    require_bool(reporting.get("automatic_submission"), "reporting.automatic_submission")
    return ScopeConfig(
        schema_version=schema_version,
        scope_id=scope_id,
        program_alias=program_alias,
        sponsor_alias=sponsor_alias,
        operator_alias=operator_alias,
        targets=tuple(targets),
        panels=tuple(panels),
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
            "policy_sha256",
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
        "policy_sha256",
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


def parse_operator_approval(approval: dict[str, Any]) -> OperatorApproval:
    _reject_unknown(
        approval,
        {
            "schema_version",
            "approval_id",
            "operator_alias",
            "decision",
            "approved_at_utc",
            "valid_until_utc",
            "scope_sha256",
            "authorization_reference",
            "objective_ids",
            "campaign_ids",
        },
        "operator approval",
    )
    schema_version = require_text(approval.get("schema_version"), "schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ConfigError(f"unsupported schema_version: {schema_version}")
    decision = require_text(approval.get("decision"), "decision")
    if decision not in {"approved", "denied"}:
        raise ConfigError("decision must be approved or denied")
    objective_ids = require_text_list(approval.get("objective_ids"), "objective_ids")
    campaign_ids = require_text_list(approval.get("campaign_ids"), "campaign_ids")
    _validate_unique(objective_ids, "objective_ids")
    _validate_unique(campaign_ids, "campaign_ids")
    if not objective_ids and not campaign_ids:
        raise ConfigError("operator approval must name at least one objective or campaign")
    return OperatorApproval(
        approval_id=require_text(approval.get("approval_id"), "approval_id"),
        operator_alias=require_text(approval.get("operator_alias"), "operator_alias"),
        decision=decision,
        approved_at_utc=require_text(approval.get("approved_at_utc"), "approved_at_utc"),
        valid_until_utc=require_text(approval.get("valid_until_utc"), "valid_until_utc"),
        scope_sha256=require_text(approval.get("scope_sha256"), "scope_sha256"),
        authorization_reference=require_text(
            approval.get("authorization_reference"), "authorization_reference"
        ),
        objective_ids=tuple(objective_ids),
        campaign_ids=tuple(campaign_ids),
        data=approval,
    )


def parse_review_decision(review: dict[str, Any]) -> ReviewDecision:
    allowed = {
        "schema_version",
        "decision_id",
        "campaign_id",
        "objective_id",
        "operator_alias",
        "decision",
        "decided_at_utc",
        "state_sha256",
        "reason",
    }
    unknown = sorted(set(review) - allowed)
    if unknown:
        raise ConfigError(f"review decision contains unknown fields: {', '.join(unknown)}")
    schema_version = require_text(review.get("schema_version"), "schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ConfigError(f"unsupported schema_version: {schema_version}")
    decision = require_text(review.get("decision"), "decision")
    if decision not in {"approved", "denied", "stop"}:
        raise ConfigError("review decision must be approved, denied, or stop")
    state_sha256 = require_text(review.get("state_sha256"), "state_sha256")
    if len(state_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in state_sha256
    ):
        raise ConfigError("state_sha256 must be a lowercase SHA256 digest")
    return ReviewDecision(
        decision_id=require_text(review.get("decision_id"), "decision_id"),
        campaign_id=require_text(review.get("campaign_id"), "campaign_id"),
        objective_id=require_text(review.get("objective_id"), "objective_id"),
        operator_alias=require_text(review.get("operator_alias"), "operator_alias"),
        decision=decision,
        decided_at_utc=require_text(review.get("decided_at_utc"), "decided_at_utc"),
        state_sha256=state_sha256,
        reason=require_text(review.get("reason"), "reason"),
        data=review,
    )
