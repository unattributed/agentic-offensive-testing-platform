"""Authoritative policy gate for every proposed execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ConfigError, validate_scope_shape


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


def evaluate(
    scope: dict[str, Any] | None,
    objective: dict[str, Any] | None = None,
    *,
    live: bool = False,
    operator_approved: bool = False,
    workspace: str | Path | None = None,
    redaction_passed: bool = True,
) -> PolicyDecision:
    reasons: list[str] = []
    if scope is None:
        return PolicyDecision(False, ("scope is missing",))
    try:
        validate_scope_shape(scope)
    except ConfigError as exc:
        return PolicyDecision(False, (str(exc),))

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
        required_refs = (
            ("authorization reference", authorization.get("reference")),
            ("bug bounty style agreement or equivalent authorization reference", authorization.get("agreement_reference")),
            ("program profile reference", authorization.get("program_profile_reference")),
            ("rules-of-engagement reference", roe.get("reference")),
        )
        if not authorization.get("live_authorized"):
            reasons.append("live mode lacks explicit live authorization")
        for label, value in required_refs:
            if not _non_placeholder(value):
                reasons.append(f"{label} is missing")
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

    return PolicyDecision(not reasons, tuple(dict.fromkeys(reasons)))
