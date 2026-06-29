"""Authoritative policy gate for every proposed execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from .config import ConfigError, parse_program_profile, parse_scope


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


def evaluate(
    scope: dict[str, Any] | None,
    objective: dict[str, Any] | None = None,
    *,
    program_profile: dict[str, Any] | None = None,
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

    category = objective.get("category") or objective.get("module")
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

    if category == "bounded_fuzzing":
        fuzzing = scope.get("fuzzing", {})
        if not fuzzing.get("authorized"):
            reasons.append("fuzzing is not explicitly authorized")
        for field in ("payload_budget", "request_budget", "per_endpoint_limit", "max_runtime_seconds"):
            if not isinstance(fuzzing.get(field), int) or fuzzing[field] <= 0:
                reasons.append(f"fuzzing.{field} is missing")
        if objective.get("state_changing") and not fuzzing.get("state_changing_authorized"):
            reasons.append("state-changing fuzzing is not explicitly authorized")

    if category == "service_control_panel" and not scope.get("service_control_panels", {}).get("authorized"):
        reasons.append("service control panel testing is not explicitly authorized")

    if category == "sbom_review":
        provided = set(scope.get("provided_artifacts", []))
        if not objective.get("artifact") or objective.get("artifact") not in provided:
            reasons.append("SBOM or configuration artifact was not provided")

    if category == "crypto_controls" and not scope.get("cryptographic_controls", {}).get("authorized"):
        reasons.append("cryptographic controls review is not explicitly scoped")

    if objective.get("requires_human_approval") and not objective.get("human_approved"):
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
        confidentiality = authorization.get("confidentiality", {})
        if confidentiality.get("required") and (
            not confidentiality.get("confirmed") or not _non_placeholder(confidentiality.get("reference"))
        ):
            reasons.append("required confidentiality confirmation is missing")
        if not operator_approved:
            reasons.append("operator approval is missing")
        if not scope.get("allowed_test_windows"):
            reasons.append("allowed test windows are missing")
        if not scope.get("reporting", {}).get("disclosure_rules"):
            reasons.append("reporting and disclosure rules are missing")
        if not scope.get("stop_conditions"):
            reasons.append("emergency stop conditions are missing")
        if parsed_profile is not None:
            if parsed_profile.program_alias != parsed_scope.program_alias:
                reasons.append("program profile alias does not match scope")
            profile_reference = program_profile.get("authorization_reference")
            if authorization.get("reference") != profile_reference:
                reasons.append("authorization reference does not match program profile")
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
