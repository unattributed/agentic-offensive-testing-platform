"""Authoritative policy gate for every proposed execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import re
from pathlib import Path
from typing import Any

from .config import ConfigError, parse_operator_approval, parse_program_profile, parse_scope
from .bounded_fuzzing import (
    collect_fuzzing_actions,
    collect_fuzzing_stop_signals,
    fuzzing_boundary_errors,
)
from .crypto_review import crypto_action_is_unsafe, crypto_evidence_errors
from .control_panel import (
    collect_panel_actions,
    collect_panel_observations,
    denied_panel_actions,
    panel_lockout_risk_detected,
    unsafe_panel_observations,
)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reasons: tuple[str, ...]

    @property
    def summary(self) -> str:
        return "allowed" if self.allowed else "; ".join(self.reasons)


def _non_placeholder(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    lowered = value.lower()
    return not any(marker in lowered for marker in ("replace-me", "placeholder", "example-only"))


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _parse_utc(value: Any, field: str, reasons: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        reasons.append(f"{field} is missing")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        reasons.append(f"{field} is not a valid ISO-8601 timestamp")
        return None
    if parsed.tzinfo is None:
        reasons.append(f"{field} must include a timezone")
        return None
    return parsed.astimezone(UTC)


def _parse_date(value: Any, field: str, reasons: list[str]) -> date | None:
    if not isinstance(value, str) or not value.strip():
        reasons.append(f"{field} is missing")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        reasons.append(f"{field} is not a valid ISO date")
        return None


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _domain_allowed(domain: str, patterns: list[str]) -> bool:
    candidate = domain.lower().rstrip(".")
    for raw_pattern in patterns:
        pattern = raw_pattern.lower().rstrip(".")
        if pattern.startswith("*."):
            suffix = pattern[2:]
            if candidate.endswith("." + suffix) and candidate != suffix:
                return True
        elif candidate == pattern:
            return True
    return False


def evaluate(
    scope: dict[str, Any] | None,
    objective: dict[str, Any] | None = None,
    *,
    program_profile: dict[str, Any] | None = None,
    operator_approval: dict[str, Any] | None = None,
    scope_sha256: str | None = None,
    campaign_id: str | None = None,
    live: bool = False,
    operator_approved: bool = False,
    workspace: str | Path | None = None,
    redaction_passed: bool = True,
    now: datetime | None = None,
) -> PolicyDecision:
    reasons: list[str] = []
    if scope is None:
        return PolicyDecision(False, ("scope is missing",))
    try:
        parsed_scope = parse_scope(scope)
    except ConfigError as exc:
        return PolicyDecision(False, (str(exc),))

    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    objective = objective or {}
    authorization = scope["authorization"]
    roe = scope["rules_of_engagement"]
    rate_limits = scope["rate_limits"]
    evidence = scope["evidence"]
    allowed_targets = scope["allowed_targets"]
    forbidden = set(scope["forbidden_actions"])
    allowed_categories = set(scope["allowed_categories"])

    target_alias = objective.get("target_alias")
    target = next(
        (entry for entry in allowed_targets if isinstance(entry, dict) and entry.get("alias") == target_alias),
        None,
    )
    if target_alias and target is None:
        reasons.append("target is not explicitly allowlisted")
    if live and not target_alias:
        reasons.append("live objective target alias is missing")

    module = objective.get("module")
    category = objective.get("category") or module
    if module and category and module != category:
        reasons.append("objective category must match module")
    if category and category not in allowed_categories:
        reasons.append("test category is not explicitly allowlisted")

    action = objective.get("action")
    if action in forbidden:
        reasons.append("action is forbidden")

    service = objective.get("service")
    if service and (target is None or service not in target.get("services", [])):
        reasons.append("service is not explicitly allowlisted")
    api = objective.get("api")
    if api and (target is None or api not in target.get("apis", [])):
        reasons.append("API is not explicitly allowlisted")
    environment = objective.get("environment")
    if environment and (target is None or environment not in target.get("environments", [])):
        reasons.append("environment is not explicitly allowlisted")
    account_alias = objective.get("account_alias")
    if account_alias and (target is None or account_alias not in target.get("approved_account_aliases", [])):
        reasons.append("test account is not explicitly approved")
    domain = objective.get("domain")
    if domain and (target is None or not _domain_allowed(str(domain), target.get("domains", []))):
        reasons.append("domain is not explicitly allowlisted")
    network_categories = {"wstg_webapp", "service_control_panel", "bounded_fuzzing"}
    if live and category in network_categories:
        if not domain:
            reasons.append("live network objective domain is missing")
        if not service:
            reasons.append("live network objective service is missing")

    if category == "bounded_fuzzing":
        fuzzing = scope.get("fuzzing", {})
        if not fuzzing.get("authorized"):
            reasons.append("fuzzing is not explicitly authorized")
        requested_fuzzing_actions = collect_fuzzing_actions(objective)
        if not requested_fuzzing_actions:
            reasons.append("fuzzing action is missing")
        approved_fuzzing_actions = set(fuzzing.get("approved_actions", []))
        denied_fuzzing_actions = set(fuzzing.get("denied_actions", []))
        explicitly_denied = sorted(
            action
            for action in requested_fuzzing_actions
            if action in denied_fuzzing_actions
        )
        if explicitly_denied:
            reasons.append(
                "fuzzing action is explicitly denied by scope: "
                + ", ".join(explicitly_denied)
            )
        unapproved_fuzzing_actions = sorted(
            action
            for action in requested_fuzzing_actions
            if action not in approved_fuzzing_actions
            and action not in denied_fuzzing_actions
        )
        if unapproved_fuzzing_actions:
            reasons.append(
                "fuzzing action is not explicitly approved: "
                + ", ".join(unapproved_fuzzing_actions)
            )
        for field in ("payload_budget", "request_budget", "per_endpoint_limit", "max_runtime_seconds"):
            if not isinstance(fuzzing.get(field), int) or fuzzing[field] <= 0:
                reasons.append(f"fuzzing.{field} is missing")
        reasons.extend(fuzzing_boundary_errors(objective, fuzzing))
        stop_signals = collect_fuzzing_stop_signals(objective)
        if stop_signals:
            reasons.append(
                "fuzzing stop condition detected: " + ", ".join(sorted(stop_signals))
            )
        if objective.get("state_changing") and not fuzzing.get("state_changing_authorized"):
            reasons.append("state-changing fuzzing is not explicitly authorized")

    if category == "service_control_panel" or module == "service_control_panel":
        panel_config = scope.get("service_control_panels", {})
        if not panel_config.get("authorized"):
            reasons.append("service control panel testing is not explicitly authorized")
        panel_alias = objective.get("panel_alias")
        raw_panels = panel_config.get("panels", [])
        panel = next(
            (entry for entry in raw_panels if isinstance(entry, dict) and entry.get("alias") == panel_alias),
            None,
        )
        unsafe_panel_actions = sorted(denied_panel_actions(objective))
        if not panel_alias:
            reasons.append("panel alias is missing")
        elif panel is None:
            reasons.append("panel alias is not explicitly allowlisted")
        else:
            if target_alias != panel.get("target_alias"):
                reasons.append("panel target alias does not match objective")
            objective_panel_type = objective.get("panel_type")
            if not objective_panel_type:
                reasons.append("panel type is missing")
            elif objective_panel_type != panel.get("panel_type"):
                reasons.append("panel type does not match scoped panel")
            approved_actions = set(panel.get("approved_actions", []))
            configured_denials = set(panel.get("denied_actions", []))
            configured_denied_actions = sorted(
                action for action in collect_panel_actions(objective) if action in configured_denials
            )
            if configured_denied_actions:
                reasons.append(
                    "panel action is explicitly denied by scope: "
                    + ", ".join(configured_denied_actions)
                )
            unapproved_actions = sorted(
                action
                for action in collect_panel_actions(objective)
                if action not in approved_actions
                and action not in unsafe_panel_actions
                and action not in configured_denials
            )
            if unapproved_actions:
                reasons.append("panel action is not explicitly approved: " + ", ".join(unapproved_actions))
        if unsafe_panel_actions:
            reasons.append(
                "panel action is denied by safety boundary: " + ", ".join(unsafe_panel_actions)
            )
        unsafe_observations = sorted(unsafe_panel_observations(objective))
        if unsafe_observations:
            reasons.append(
                "panel observation is not approved as safe: " + ", ".join(unsafe_observations)
            )
        if (
            "plan_safe_panel_observations" in collect_panel_actions(objective)
            and not collect_panel_observations(objective)
        ):
            reasons.append("safe panel observation planning requires requested_observations")
        if panel_lockout_risk_detected(objective) and not objective.get("human_approved"):
            reasons.append("authentication lockout risk requires human approval")

    if category == "sbom_review":
        provided = set(scope.get("provided_artifacts", []))
        if not objective.get("artifact") or objective.get("artifact") not in provided:
            reasons.append("SBOM or configuration artifact was not provided")
        artifact = objective.get("artifact")
        if isinstance(artifact, str):
            artifact_path = Path(artifact)
            if artifact_path.is_absolute() or ".." in artifact_path.parts:
                reasons.append("provided artifact path must remain relative")
        if objective.get("vulnerability_data_source") is not None:
            source = objective.get("vulnerability_data_source")
            if not isinstance(source, dict) or source.get("network_lookup") is not False:
                reasons.append("vulnerability mapping requires an offline configured data source")

    if category == "crypto_controls":
        crypto = scope.get("cryptographic_controls", {})
        if not crypto.get("authorized"):
            reasons.append("cryptographic controls review is not explicitly scoped")
        action = objective.get("action")
        if not action:
            reasons.append("cryptographic controls action is missing")
        elif action in set(crypto.get("denied_actions", [])) or crypto_action_is_unsafe(action):
            reasons.append("cryptographic controls action is explicitly denied")
        elif action not in set(crypto.get("approved_actions", [])):
            reasons.append("cryptographic controls action is not explicitly approved")
        reasons.extend(crypto_evidence_errors(objective))

    if objective.get("requires_human_approval") and not live and not objective.get("human_approved"):
        reasons.append("human approval is required")

    if not rate_limits or not all(
        isinstance(rate_limits.get(field), int) and rate_limits[field] > 0
        for field in ("requests_per_minute", "max_requests")
    ):
        reasons.append("rate limits are missing or invalid")

    root = Path(workspace or Path.cwd()).resolve()
    evidence_path = Path(evidence["workspace"])
    if not evidence_path.is_absolute():
        evidence_path = root / evidence_path
    if not _inside(evidence_path, root):
        reasons.append("evidence directory is outside the configured workspace")
    if not redaction_passed:
        reasons.append("redaction checks failed")

    if live:
        parsed_profile = None
        if program_profile is None:
            reasons.append("private program profile is missing")
        else:
            try:
                parsed_profile = parse_program_profile(program_profile)
            except ConfigError as exc:
                reasons.append(f"program profile is invalid: {exc}")
        required_refs = (
            ("authorization reference", authorization.get("reference")),
            ("bug bounty style agreement or equivalent authorization reference", authorization.get("agreement_reference")),
            ("program profile reference", authorization.get("program_profile_reference")),
            ("rules-of-engagement reference", roe.get("reference")),
        )
        if not authorization.get("live_authorized"):
            reasons.append("live mode lacks explicit live authorization")
        if authorization.get("type") not in {
            "bug_bounty_program",
            "written_authorization",
            "evaluator_authorization",
            "client_authorization",
        }:
            reasons.append("authorization type is missing or unsupported")
        for label, value in required_refs:
            if not _non_placeholder(value):
                reasons.append(f"{label} is missing")
        issued_at = _parse_utc(authorization.get("issued_at_utc"), "authorization issued_at_utc", reasons)
        valid_from = _parse_utc(authorization.get("valid_from_utc"), "authorization valid_from_utc", reasons)
        valid_until = _parse_utc(authorization.get("valid_until_utc"), "authorization valid_until_utc", reasons)
        if issued_at and valid_from and issued_at > valid_from:
            reasons.append("authorization was issued after its validity start")
        if valid_from and valid_until and valid_from >= valid_until:
            reasons.append("authorization validity interval is invalid")
        if valid_from and current_time < valid_from:
            reasons.append("authorization is not yet valid")
        if valid_until and current_time >= valid_until:
            reasons.append("authorization has expired")
        if not roe.get("confirmed"):
            reasons.append("rules-of-engagement confirmation is missing")
        confirmed_at = _parse_utc(roe.get("confirmed_at_utc"), "rules-of-engagement confirmed_at_utc", reasons)
        if confirmed_at and confirmed_at > current_time:
            reasons.append("rules-of-engagement confirmation is in the future")
        if not _valid_sha256(roe.get("policy_sha256")):
            reasons.append("rules-of-engagement policy SHA256 is missing or invalid")
        if not roe.get("prohibited_actions_acknowledged"):
            reasons.append("prohibited actions were not acknowledged")
        if not roe.get("evidence_handling_confirmed"):
            reasons.append("evidence handling requirements were not confirmed")
        if not _non_placeholder(roe.get("emergency_contact_reference")):
            reasons.append("emergency contact reference is missing")
        if not roe.get("target_instability_stop"):
            reasons.append("target instability stop is not confirmed")
        if not roe.get("authentication_lockout_stop"):
            reasons.append("authentication lockout stop is not confirmed")
        confidentiality = authorization.get("confidentiality", {})
        if confidentiality.get("required") and (
            not confidentiality.get("confirmed") or not _non_placeholder(confidentiality.get("reference"))
        ):
            reasons.append("required confidentiality confirmation is missing")
        if not operator_approved:
            reasons.append("operator approval is missing")
        parsed_approval = None
        if operator_approval is None:
            reasons.append("private operator approval record is missing")
        else:
            try:
                parsed_approval = parse_operator_approval(operator_approval)
            except ConfigError as exc:
                reasons.append(f"operator approval record is invalid: {exc}")
        if parsed_approval is not None:
            approved_at = _parse_utc(
                parsed_approval.approved_at_utc,
                "operator approval approved_at_utc",
                reasons,
            )
            approval_expires = _parse_utc(
                parsed_approval.valid_until_utc,
                "operator approval valid_until_utc",
                reasons,
            )
            if parsed_approval.decision != "approved":
                reasons.append("operator approval decision is not approved")
            if approved_at and approved_at > current_time:
                reasons.append("operator approval is not yet valid")
            if approval_expires and current_time >= approval_expires:
                reasons.append("operator approval has expired")
            if approved_at and approval_expires and approved_at >= approval_expires:
                reasons.append("operator approval validity interval is invalid")
            if parsed_approval.operator_alias != parsed_scope.operator_alias:
                reasons.append("operator approval alias does not match scope")
            if parsed_approval.authorization_reference != authorization.get("reference"):
                reasons.append("operator approval authorization reference does not match scope")
            if not _valid_sha256(parsed_approval.scope_sha256) or parsed_approval.scope_sha256 != scope_sha256:
                reasons.append("operator approval scope SHA256 does not match scope file")
            objective_id = objective.get("id")
            objective_approved = bool(objective_id and objective_id in parsed_approval.objective_ids)
            campaign_approved = bool(campaign_id and campaign_id in parsed_approval.campaign_ids)
            if not objective_approved and not campaign_approved:
                reasons.append("operator approval does not cover this objective or campaign")
        windows = scope.get("allowed_test_windows", [])
        if not windows:
            reasons.append("allowed test windows are missing")
        active_window = False
        for index, window in enumerate(windows):
            start = _parse_utc(window.get("start_utc"), f"allowed_test_windows[{index}].start_utc", reasons)
            end = _parse_utc(window.get("end_utc"), f"allowed_test_windows[{index}].end_utc", reasons)
            if start and end:
                if start >= end:
                    reasons.append(f"allowed_test_windows[{index}] interval is invalid")
                elif start <= current_time < end:
                    active_window = True
        if windows and not active_window:
            reasons.append("current time is outside all allowed test windows")
        if not scope.get("reporting", {}).get("disclosure_rules"):
            reasons.append("reporting and disclosure rules are missing")
        reporting = scope.get("reporting", {})
        if not reporting.get("human_review_required"):
            reasons.append("human report review is not required")
        if reporting.get("automatic_submission"):
            reasons.append("automatic report submission is forbidden")
        required_stops = {
            "operator_stop",
            "policy_denial",
            "instability",
            "authentication_lockout_risk",
            "redaction_failure",
        }
        stop_conditions = set(scope.get("stop_conditions", []))
        if not stop_conditions:
            reasons.append("emergency stop conditions are missing")
        elif missing_stops := sorted(required_stops - stop_conditions):
            reasons.append("required stop conditions are missing: " + ", ".join(missing_stops))
        if parsed_profile is not None:
            checklist = parsed_profile.policy_checklist
            if not checklist.policy_accepted:
                reasons.append("program policy acceptance is not confirmed")
            if not checklist.safe_harbor_reviewed:
                reasons.append("program safe harbor review is not confirmed")
            if not checklist.disclosure_rules_reviewed:
                reasons.append("program disclosure rules review is not confirmed")
            if not checklist.stop_conditions_reviewed:
                reasons.append("program stop conditions review is not confirmed")
            if parsed_profile.program_alias != parsed_scope.program_alias:
                reasons.append("program profile alias does not match scope")
            profile_reference = program_profile.get("authorization_reference")
            if authorization.get("reference") != profile_reference:
                reasons.append("authorization reference does not match program profile")
            if roe.get("policy_sha256") != program_profile.get("policy_sha256"):
                reasons.append("rules-of-engagement policy SHA256 does not match program profile")
            accepted_date = _parse_date(
                program_profile.get("accepted_policy_date"),
                "program profile accepted_policy_date",
                reasons,
            )
            if accepted_date and accepted_date > current_time.date():
                reasons.append("program policy acceptance date is in the future")
            if target_alias:
                if target_alias in parsed_profile.out_of_scope_asset_aliases:
                    reasons.append("target is explicitly out of scope in program profile")
                if target_alias not in parsed_profile.in_scope_asset_aliases:
                    reasons.append("target is not in scope in program profile")
            if category:
                if category in parsed_profile.forbidden_testing_categories:
                    reasons.append("test category is forbidden by program profile")
                if category not in parsed_profile.allowed_testing_categories:
                    reasons.append("test category is not allowed by program profile")
            if action in parsed_profile.prohibited_actions:
                reasons.append("action is prohibited by program profile")
            profile_rate = program_profile["rate_limits"]["requests_per_minute"]
            if rate_limits["requests_per_minute"] > profile_rate:
                reasons.append("scope rate limit exceeds program profile limit")

    return PolicyDecision(not reasons, tuple(dict.fromkeys(reasons)))
