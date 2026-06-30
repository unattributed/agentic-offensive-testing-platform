"""Report review gating for evidence-bound finding promotion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PANEL_EVIDENCE_MODULE = "service_control_panel"
PANEL_EVIDENCE_ARTIFACT_ROLE = "service_control_panel_evidence_record"
REVIEW_STATUSES = {"not_required", "candidate_reviewed", "excluded_pending_review"}
AUTOMATION_REVIEWERS = {"", "system", "automation", "automated"}


@dataclass(frozen=True)
class ReportReviewGate:
    review_required: bool
    allowed: bool
    status: str
    reason: str
    reviewer: str | None = None


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def manifest_requires_report_review(manifest: Any) -> bool:
    """Return true when evidence must be held behind report-review gating."""
    if getattr(manifest, "module_name", None) == PANEL_EVIDENCE_MODULE:
        return True
    response_metadata = getattr(manifest, "response_metadata", {})
    if isinstance(response_metadata, dict) and isinstance(
        response_metadata.get("observation_plan"), dict
    ):
        return True
    for artifact in getattr(manifest, "artifacts", []):
        if isinstance(artifact, dict) and artifact.get("role") == PANEL_EVIDENCE_ARTIFACT_ROLE:
            return True
    return False


def evaluate_report_review_gate(
    manifest: Any,
    *,
    report_reviewed: bool = False,
    reviewer: str | None = None,
) -> ReportReviewGate:
    """Evaluate whether evidence may be promoted to a finding candidate."""
    if not manifest_requires_report_review(manifest):
        return ReportReviewGate(
            review_required=False,
            allowed=True,
            status="not_required",
            reason="report review is not required for this evidence type",
            reviewer=None,
        )
    reviewer_name = _text(reviewer)
    if not report_reviewed:
        return ReportReviewGate(
            review_required=True,
            allowed=False,
            status="excluded_pending_review",
            reason="panel evidence requires explicit human review before finding candidate creation",
            reviewer=None,
        )
    if reviewer_name.lower() in AUTOMATION_REVIEWERS:
        return ReportReviewGate(
            review_required=True,
            allowed=False,
            status="excluded_pending_review",
            reason="panel evidence review requires a named human reviewer",
            reviewer=None,
        )
    return ReportReviewGate(
        review_required=True,
        allowed=True,
        status="candidate_reviewed",
        reason="panel evidence was explicitly reviewed before finding candidate creation",
        reviewer=reviewer_name,
    )


def report_inclusion_allowed(candidate: Any) -> bool:
    """Return true only when a candidate may appear in a generated report."""
    if not bool(getattr(candidate, "report_review_required", False)):
        return True
    return (
        getattr(candidate, "state", None) == "ready_for_report"
        and bool(getattr(candidate, "human_validated", False))
        and getattr(candidate, "report_review_status", None) == "candidate_reviewed"
        and bool(_text(getattr(candidate, "report_reviewer", None)))
    )
