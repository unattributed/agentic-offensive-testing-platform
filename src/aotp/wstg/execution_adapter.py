"""WSTG execution adapter contracts for evidence-producing campaign checks.

This module intentionally defines contracts and conversion helpers. It does not
execute network requests. Live execution remains delegated to governed tools or
application-specific runners that supply already-redacted evidence references.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Protocol

from .coverage import CoverageDisposition, CoverageRecord, CoverageTracker
from .objective_generator import WSTGObjective
from .strategy_map import ExecutableFamily


class WSTGExecutionAdapterError(ValueError):
    """Raised when a WSTG execution adapter contract is unsafe or incomplete."""


class WSTGExecutionStatus(str, Enum):
    """Generic execution result status for one WSTG objective."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"
    NOT_APPLICABLE = "not_applicable"


class WSTGAdapterKind(str, Enum):
    """Execution adapter source for a generated WSTG objective."""

    GOVERNED_TOOL = "governed_tool"
    APP_SPECIFIC_RUNNER = "app_specific_runner"


class WSTGEvidenceRole(str, Enum):
    """Allowed evidence roles produced by adapters."""

    REQUEST = "request"
    RESPONSE = "response"
    LOG = "log"
    SUMMARY = "summary"
    SCREENSHOT = "screenshot"


_ALLOWED_EVIDENCE_CLASSIFICATIONS = {
    "public",
    "restricted",
    "poc_sensitive",
    "recipient_only",
}
_ALLOWED_EXECUTION_MODES = {"not_executed", "dry_run", "live_stub", "live"}
_ALLOWED_SEVERITIES = {"unrated", "informational", "low", "medium", "high", "critical"}
_ALLOWED_CONFIDENCES = {"low", "medium", "high"}


@dataclass(frozen=True)
class WSTGRedactedEvidenceArtifact:
    """Reference to adapter evidence that has already passed redaction."""

    artifact_id: str
    role: WSTGEvidenceRole
    reference: str
    media_type: str
    classification: str
    raw_sha256: str | None = None
    redacted_sha256: str | None = None
    redacted: bool = True

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise WSTGExecutionAdapterError("evidence artifact_id is required")
        if not self.reference.strip():
            raise WSTGExecutionAdapterError("evidence reference is required")
        if self.reference.startswith("/"):
            raise WSTGExecutionAdapterError("evidence references must be relative or vault handles")
        if not self.reference.startswith("vault://"):
            path = PurePosixPath(self.reference)
            if ".." in path.parts:
                raise WSTGExecutionAdapterError("evidence references must not escape the evidence root")
        if not self.media_type.strip():
            raise WSTGExecutionAdapterError("evidence media_type is required")
        if self.classification not in _ALLOWED_EVIDENCE_CLASSIFICATIONS:
            raise WSTGExecutionAdapterError("unsupported evidence classification for adapter artifact")
        if self.redacted is not True:
            raise WSTGExecutionAdapterError("adapter evidence must reference redacted artifacts")
        for name, digest in (("raw_sha256", self.raw_sha256), ("redacted_sha256", self.redacted_sha256)):
            if digest is not None and (len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)):
                raise WSTGExecutionAdapterError(f"{name} must be a lowercase SHA256 digest")

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "role": self.role.value,
            "reference": self.reference,
            "media_type": self.media_type,
            "classification": self.classification,
            "raw_sha256": self.raw_sha256,
            "redacted_sha256": self.redacted_sha256,
            "redacted": self.redacted,
        }


@dataclass(frozen=True)
class WSTGExecutionRequest:
    """A governed request to execute one WSTG objective through an adapter."""

    objective: WSTGObjective
    adapter_kind: WSTGAdapterKind
    executor_name: str
    arguments: dict[str, Any]
    request_budget: int
    approval_reference: str
    execution_mode: str = "dry_run"
    evidence_classification: str = "restricted"

    def __post_init__(self) -> None:
        if not self.executor_name.strip():
            raise WSTGExecutionAdapterError("executor_name is required")
        if not self.approval_reference.strip():
            raise WSTGExecutionAdapterError("approval_reference is required")
        if self.request_budget < 0:
            raise WSTGExecutionAdapterError("request_budget must be non-negative")
        if self.execution_mode not in _ALLOWED_EXECUTION_MODES:
            raise WSTGExecutionAdapterError("unsupported execution mode")
        if self.execution_mode == "live" and self.request_budget < 1:
            raise WSTGExecutionAdapterError("live adapter requests require a positive request budget")
        if self.evidence_classification not in _ALLOWED_EVIDENCE_CLASSIFICATIONS:
            raise WSTGExecutionAdapterError("unsupported execution evidence classification")

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective.as_dict(),
            "adapter_kind": self.adapter_kind.value,
            "executor_name": self.executor_name,
            "arguments": dict(self.arguments),
            "request_budget": self.request_budget,
            "approval_reference": self.approval_reference,
            "execution_mode": self.execution_mode,
            "evidence_classification": self.evidence_classification,
        }


@dataclass(frozen=True)
class WSTGFindingCandidate:
    """Evidence-bound finding candidate produced only from failed checks."""

    candidate_id: str
    objective_id: str
    wstg_id: str
    title: str
    summary: str
    severity_candidate: str
    confidence: str
    evidence_references: tuple[str, ...]
    state: str = "candidate"

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise WSTGExecutionAdapterError("finding candidate_id is required")
        if self.state != "candidate":
            raise WSTGExecutionAdapterError("adapter finding candidates must remain candidate state")
        if self.severity_candidate not in _ALLOWED_SEVERITIES:
            raise WSTGExecutionAdapterError("unsupported severity candidate")
        if self.confidence not in _ALLOWED_CONFIDENCES:
            raise WSTGExecutionAdapterError("unsupported finding confidence")
        if not self.evidence_references:
            raise WSTGExecutionAdapterError("finding candidates require evidence references")

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "objective_id": self.objective_id,
            "wstg_id": self.wstg_id,
            "title": self.title,
            "summary": self.summary,
            "severity_candidate": self.severity_candidate,
            "confidence": self.confidence,
            "evidence_references": list(self.evidence_references),
            "state": self.state,
        }


@dataclass(frozen=True)
class WSTGExecutionResult:
    """Generic execution result for one generated WSTG objective."""

    request: WSTGExecutionRequest
    status: WSTGExecutionStatus
    summary: str
    evidence: tuple[WSTGRedactedEvidenceArtifact, ...] = ()
    reasons: tuple[str, ...] = ()
    finding_candidate: WSTGFindingCandidate | None = None

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise WSTGExecutionAdapterError("execution result summary is required")
        if self.status in {WSTGExecutionStatus.PASS, WSTGExecutionStatus.FAIL} and not self.evidence:
            raise WSTGExecutionAdapterError("pass and fail results require redacted evidence")
        if self.status in {WSTGExecutionStatus.SKIP, WSTGExecutionStatus.NOT_APPLICABLE} and not self.reasons:
            raise WSTGExecutionAdapterError("skip and not_applicable results require reasons")
        if self.finding_candidate is not None:
            if self.status is not WSTGExecutionStatus.FAIL:
                raise WSTGExecutionAdapterError("finding candidates are only allowed for fail results")
            evidence_refs = {artifact.reference for artifact in self.evidence}
            if not set(self.finding_candidate.evidence_references).issubset(evidence_refs):
                raise WSTGExecutionAdapterError("finding candidate must reference result evidence")
            if self.finding_candidate.objective_id != self.request.objective.objective_id:
                raise WSTGExecutionAdapterError("finding candidate objective does not match result")

    @property
    def evidence_references(self) -> tuple[str, ...]:
        return tuple(artifact.reference for artifact in self.evidence)

    @property
    def coverage_disposition(self) -> CoverageDisposition:
        if self.status in {WSTGExecutionStatus.PASS, WSTGExecutionStatus.FAIL, WSTGExecutionStatus.WARNING}:
            return CoverageDisposition.TESTED
        if self.status is WSTGExecutionStatus.SKIP:
            return CoverageDisposition.SKIPPED
        return CoverageDisposition.SKIPPED

    @property
    def coverage_reasons(self) -> tuple[str, ...]:
        if self.status is WSTGExecutionStatus.NOT_APPLICABLE:
            return self.reasons or ("not applicable to target",)
        if self.status is WSTGExecutionStatus.SKIP:
            return self.reasons or ("execution skipped",)
        if self.status is WSTGExecutionStatus.WARNING:
            return self.reasons or ("warning result requires review",)
        return self.reasons

    def as_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.as_dict(),
            "status": self.status.value,
            "summary": self.summary,
            "evidence": [artifact.as_dict() for artifact in self.evidence],
            "reasons": list(self.reasons),
            "coverage_disposition": self.coverage_disposition.value,
            "finding_candidate": self.finding_candidate.as_dict() if self.finding_candidate else None,
        }


class WSTGExecutionAdapter(Protocol):
    """Protocol implemented by governed tools and app-specific WSTG runners."""

    adapter_id: str
    supported_families: tuple[ExecutableFamily, ...]

    def execute(self, request: WSTGExecutionRequest) -> WSTGExecutionResult:
        """Execute a prepared request and return redacted evidence references."""



def build_execution_request(
    objective: WSTGObjective,
    *,
    adapter_kind: WSTGAdapterKind,
    approval_reference: str,
    executor_name: str | None = None,
    argument_overrides: dict[str, Any] | None = None,
    request_budget: int = 0,
    execution_mode: str = "dry_run",
) -> WSTGExecutionRequest:
    """Convert a generated objective into a governed adapter request."""

    arguments = dict(objective.arguments)
    if argument_overrides:
        arguments.update(argument_overrides)
    return WSTGExecutionRequest(
        objective=objective,
        adapter_kind=adapter_kind,
        executor_name=executor_name or objective.tool_name,
        arguments=arguments,
        request_budget=request_budget,
        approval_reference=approval_reference,
        execution_mode=execution_mode,
        evidence_classification=objective.evidence_classification,
    )



def create_finding_candidate(
    result: WSTGExecutionResult,
    *,
    candidate_id: str,
    title: str,
    summary: str,
    severity_candidate: str = "unrated",
    confidence: str = "low",
) -> WSTGFindingCandidate:
    """Create an evidence-bound finding candidate from a failed result only."""

    if result.status is not WSTGExecutionStatus.FAIL:
        raise WSTGExecutionAdapterError("only failed WSTG execution results can create finding candidates")
    if not result.evidence_references:
        raise WSTGExecutionAdapterError("finding candidates require result evidence references")
    return WSTGFindingCandidate(
        candidate_id=candidate_id,
        objective_id=result.request.objective.objective_id,
        wstg_id=result.request.objective.wstg_id,
        title=title,
        summary=summary,
        severity_candidate=severity_candidate,
        confidence=confidence,
        evidence_references=result.evidence_references,
    )



def coverage_record_from_execution_result(result: WSTGExecutionResult) -> CoverageRecord:
    """Convert an adapter result into a Sprint 17 coverage record."""

    objective = result.request.objective
    disposition = result.coverage_disposition
    evidence_references = result.evidence_references if disposition is CoverageDisposition.TESTED else ()
    reasons = result.coverage_reasons
    if disposition is not CoverageDisposition.TESTED and not reasons:
        reasons = (result.status.value,)
    return CoverageRecord(
        objective_id=objective.objective_id,
        wstg_id=objective.wstg_id,
        phase=objective.phase,
        disposition=disposition,
        evidence_references=evidence_references,
        reasons=reasons,
    )



def apply_execution_result_to_coverage(tracker: CoverageTracker, result: WSTGExecutionResult) -> CoverageRecord:
    """Record an adapter result in the campaign coverage ledger."""

    record = coverage_record_from_execution_result(result)
    tracker.record(record)
    return record
