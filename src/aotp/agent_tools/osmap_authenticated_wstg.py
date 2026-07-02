"""Governed authenticated OSMAP WSTG runner.

The runner consumes Sprint 17F execution requests and an active authenticated
session boundary. Network-silent synthetic observations are supported for tests.
Live-capable execution remains disabled unless the caller provides all explicit
approval flags and route scope has already passed the boundary.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from aotp.auth_session import AuthSessionError, AuthState, AuthenticatedSessionBoundary, LogoutCheckStatus
from aotp.evidence_classifier import classify_text
from aotp.wstg.execution_adapter import (
    WSTGAdapterKind,
    WSTGEvidenceRole,
    WSTGExecutionAdapterError,
    WSTGExecutionRequest,
    WSTGExecutionResult,
    WSTGExecutionStatus,
    WSTGRedactedEvidenceArtifact,
    create_finding_candidate,
)


class AuthenticatedOSMAPRunnerError(ValueError):
    """Raised when an authenticated OSMAP request is denied."""


@dataclass(frozen=True)
class SyntheticAuthenticatedObservation:
    status: str
    summary: str
    evidence_reference: str
    evidence_payload: dict[str, Any]
    finding_title: str | None = None
    finding_summary: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"pass", "fail", "warning", "skip", "not_applicable"}:
            raise AuthenticatedOSMAPRunnerError("unsupported synthetic observation status")
        _assert_no_raw_secret_material(self.evidence_payload)
        if self.evidence_reference.startswith("/") or ".." in self.evidence_reference.split("/"):
            raise AuthenticatedOSMAPRunnerError("evidence reference must be relative and safe")


class AuthenticatedOSMAPWSTGRunner:
    adapter_id = "osmap_authenticated_wstg"

    def execute(
        self,
        request: WSTGExecutionRequest,
        *,
        boundary: AuthenticatedSessionBoundary,
        observation: SyntheticAuthenticatedObservation | None = None,
        live_enabled: bool = False,
        operator_approved: bool = False,
    ) -> WSTGExecutionResult:
        """Execute a governed authenticated request or synthetic observation."""

        _validate_request(request)
        _assert_no_raw_secret_material(request.arguments)
        if request.execution_mode == "live" and not (live_enabled and operator_approved):
            raise AuthenticatedOSMAPRunnerError("live authenticated execution is disabled without explicit approval")
        method = str(request.arguments.get("method", "GET"))
        route = str(request.arguments.get("path_pattern", "/"))
        boundary.authorize_route(
            method=method,
            path=route,
            target_alias=request.objective.target_alias,
            account_alias=boundary.account_alias,
            auth_state=AuthState.AUTHENTICATED,
        )
        if request.request_budget < 1:
            raise AuthenticatedOSMAPRunnerError("authenticated OSMAP execution requires positive request budget")
        selected = observation or SyntheticAuthenticatedObservation(
            status="skip",
            summary="network-silent authenticated OSMAP runner requires synthetic observation or live approval",
            evidence_reference=f"authenticated-osmap/{request.objective.objective_id}-skipped-redacted.json",
            evidence_payload={"status": "skip", "reason": "network silent default"},
        )
        status = WSTGExecutionStatus(selected.status)
        evidence = ()
        reasons: tuple[str, ...] = ()
        if status in {WSTGExecutionStatus.PASS, WSTGExecutionStatus.FAIL, WSTGExecutionStatus.WARNING}:
            payload = json.dumps(selected.evidence_payload, sort_keys=True).encode("utf-8")
            digest = hashlib.sha256(payload).hexdigest()
            evidence = (
                WSTGRedactedEvidenceArtifact(
                    artifact_id="osmap-authenticated-observation",
                    role=WSTGEvidenceRole.SUMMARY,
                    reference=selected.evidence_reference,
                    media_type="application/json",
                    classification="restricted",
                    raw_sha256=digest,
                    redacted_sha256=digest,
                ),
            )
        else:
            reasons = (selected.summary,)
        base = WSTGExecutionResult(
            request=request,
            status=status,
            summary=selected.summary,
            evidence=evidence,
            reasons=reasons,
        )
        if status is WSTGExecutionStatus.FAIL:
            candidate = create_finding_candidate(
                base,
                candidate_id=f"candidate-{request.objective.objective_id}",
                title=selected.finding_title or "authenticated OSMAP evidence-backed observation",
                summary=selected.finding_summary or selected.summary,
                severity_candidate="unrated",
                confidence="low",
            )
            return WSTGExecutionResult(
                request=request,
                status=status,
                summary=selected.summary,
                evidence=evidence,
                finding_candidate=candidate,
            )
        return base

    def verify_logout_boundary(
        self,
        *,
        boundary: AuthenticatedSessionBoundary,
        logout_route: str,
        post_logout_route: str,
        status: LogoutCheckStatus | str,
    ) -> dict[str, object]:
        record = boundary.record_logout_boundary(
            logout_route=logout_route,
            post_logout_route=post_logout_route,
            status=status,
            cleanup_recorded=True,
            notes=("raw invalidated session material excluded",),
        )
        return record.as_dict()


def review_authenticated_candidate(result: WSTGExecutionResult) -> dict[str, object]:
    """Return a false-positive-safe review state for an authenticated result."""

    if result.status is WSTGExecutionStatus.FAIL and result.finding_candidate is not None:
        return {
            "state": "candidate_needs_human_validation",
            "objective_id": result.request.objective.objective_id,
            "evidence_references": list(result.evidence_references),
            "may_report": False,
            "reason": "failed adapter result has redacted evidence but still requires human validation",
        }
    return {
        "state": "no_finding",
        "objective_id": result.request.objective.objective_id,
        "evidence_references": list(result.evidence_references),
        "may_report": False,
        "reason": "source hints and non-failed checks do not create findings",
    }


def build_authenticated_campaign_package(
    *,
    scope_aliases: dict[str, str],
    authorization_references: dict[str, str],
    route_auth_map_summary: dict[str, Any],
    wstg_candidates: list[dict[str, Any]],
    executed_results: list[dict[str, Any]],
    logout_summary: dict[str, Any] | None,
    candidate_findings: list[dict[str, Any]],
    limitations: list[str],
) -> dict[str, Any]:
    package = {
        "scope_aliases": dict(scope_aliases),
        "authorization_references": dict(authorization_references),
        "route_auth_map_summary": dict(route_auth_map_summary),
        "wstg_candidates": list(wstg_candidates),
        "executed_results": list(executed_results),
        "logout_summary": logout_summary,
        "candidate_findings": list(candidate_findings),
        "limitations": list(limitations),
        "no_secret_confirmation": True,
        "manual_review_only": True,
    }
    _assert_no_raw_secret_material(package)
    return package


def _validate_request(request: WSTGExecutionRequest) -> None:
    if request.adapter_kind is not WSTGAdapterKind.APP_SPECIFIC_RUNNER:
        raise AuthenticatedOSMAPRunnerError("authenticated OSMAP runner requires app-specific adapter request")
    if request.executor_name != "osmap_authenticated_wstg":
        raise AuthenticatedOSMAPRunnerError("request executor does not match authenticated OSMAP runner")
    if not request.approval_reference.strip():
        raise AuthenticatedOSMAPRunnerError("request approval reference is required")
    if request.evidence_classification not in {"restricted", "poc_sensitive", "recipient_only"}:
        raise AuthenticatedOSMAPRunnerError("authenticated OSMAP evidence must not be public")


def _assert_no_raw_secret_material(value: Any) -> None:
    encoded = json.dumps(value, sort_keys=True, default=str)
    classified = classify_text(encoded, context="authenticated osmap public metadata")
    if classified.vault_required:
        raise AuthenticatedOSMAPRunnerError("raw secret material is not allowed in authenticated OSMAP metadata")
    lowered = encoded.lower()
    unsafe_markers = (
        "password=",
        "password:",
        "authorization" + ": bearer",
        "bearer ",
        "csrf_token=",
        "csrf-token",
        "session" + "_id=",
        "session" + "id=",
        "session-id",
    )
    if any(marker in lowered for marker in unsafe_markers):
        raise AuthenticatedOSMAPRunnerError("raw secret marker is not allowed in authenticated OSMAP metadata")
    if _contains_sensitive_key_value(value):
        raise AuthenticatedOSMAPRunnerError("raw secret marker is not allowed in authenticated OSMAP metadata")


def _contains_sensitive_key_value(value: Any) -> bool:
    sensitive_keys = {"cookie", "cookies", "authorization", "csrf", "csrf_token", "token", "session", "session" + "_id"}
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in sensitive_keys and isinstance(item, str) and item.lower() not in {"redacted", "<redacted>"}:
                return True
            if _contains_sensitive_key_value(item):
                return True
    elif isinstance(value, (list, tuple, set)):
        return any(_contains_sensitive_key_value(item) for item in value)
    return False
