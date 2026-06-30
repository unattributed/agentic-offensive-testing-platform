"""Report review gating for evidence-bound finding promotion."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .redaction import assert_value_redacted

PANEL_EVIDENCE_MODULE = "service_control_panel"
PANEL_EVIDENCE_ARTIFACT_ROLE = "service_control_panel_evidence_record"
REVIEW_STATUSES = {"not_required", "candidate_reviewed", "excluded_pending_review"}
AUTOMATION_REVIEWERS = {
    "",
    "system",
    "automation",
    "automated",
    "bot",
    "ci",
    "ci-bot",
    "github-actions",
}
PANEL_REVIEW_DECISION = "approved_for_candidate"


@dataclass(frozen=True)
class ReportReviewGate:
    review_required: bool
    allowed: bool
    status: str
    reason: str
    reviewer: str | None = None


@dataclass
class PanelReportReviewDecision:
    decision_id: str
    evidence_manifest_sha256: str
    reviewer_alias: str
    decision: str
    decided_at_utc: str
    rationale: str
    schema_version: str = "1.0"
    decision_sha256: str | None = None

    def validate(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported panel report review schema")
        required = {
            "decision_id": self.decision_id,
            "reviewer_alias": self.reviewer_alias,
            "decided_at_utc": self.decided_at_utc,
            "rationale": self.rationale,
        }
        missing = [name for name, value in required.items() if not _text(value)]
        if missing:
            raise ValueError("panel report review fields are missing: " + ", ".join(missing))
        if self.decision != PANEL_REVIEW_DECISION:
            raise ValueError("panel report review decision is not approved for candidate creation")
        reviewer = self.reviewer_alias.strip().lower()
        if (
            reviewer in AUTOMATION_REVIEWERS
            or reviewer.endswith("-bot")
            or reviewer.endswith("_bot")
        ):
            raise ValueError("panel evidence review requires a named human reviewer")
        if (
            len(self.evidence_manifest_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.evidence_manifest_sha256)
        ):
            raise ValueError("panel report review requires a valid evidence manifest SHA256")
        try:
            decided_at = datetime.fromisoformat(self.decided_at_utc.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("panel report review timestamp is invalid") from exc
        if decided_at.tzinfo is None:
            raise ValueError("panel report review timestamp must include a timezone")
        if decided_at.astimezone(UTC) > datetime.now(UTC):
            raise ValueError("panel report review timestamp is in the future")
        assert_value_redacted(self.__dict__)
        if self.decision_sha256 is not None and self.decision_sha256 != report_review_digest(self):
            raise ValueError("panel report review integrity check failed")


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def report_review_digest(decision: PanelReportReviewDecision) -> str:
    payload = {
        "decision_id": decision.decision_id,
        "evidence_manifest_sha256": decision.evidence_manifest_sha256,
        "reviewer_alias": decision.reviewer_alias,
        "decision": decision.decision,
        "decided_at_utc": decision.decided_at_utc,
        "rationale": decision.rationale,
        "schema_version": decision.schema_version,
        "decision_sha256": None,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_report_review_decision(
    decision: PanelReportReviewDecision,
    path: str | Path,
) -> Path:
    decision.decision_sha256 = None
    decision.validate()
    decision.decision_sha256 = report_review_digest(decision)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".panel-review.", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(decision.__dict__, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
        os.chmod(output, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def load_report_review_decision(path: str | Path) -> PanelReportReviewDecision:
    try:
        decision = PanelReportReviewDecision(
            **json.loads(Path(path).read_text(encoding="utf-8"))
        )
        decision.validate()
        return decision
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"panel report review decision is invalid: {path}: {exc}") from exc


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    review_decision: PanelReportReviewDecision | None = None,
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
    if review_decision is None:
        return ReportReviewGate(
            review_required=True,
            allowed=False,
            status="excluded_pending_review",
            reason="panel evidence requires explicit human review before finding candidate creation",
            reviewer=None,
        )
    review_decision.validate()
    if review_decision.evidence_manifest_sha256 != getattr(manifest, "manifest_sha256", None):
        return ReportReviewGate(
            review_required=True,
            allowed=False,
            status="excluded_pending_review",
            reason="panel report review decision does not match the evidence manifest",
            reviewer=None,
        )
    return ReportReviewGate(
        review_required=True,
        allowed=True,
        status="candidate_reviewed",
        reason="panel evidence was explicitly reviewed before finding candidate creation",
        reviewer=review_decision.reviewer_alias,
    )


def report_inclusion_allowed(candidate: Any, manifest: Any | None = None) -> bool:
    """Return true only when a candidate may appear in a generated report."""
    review_required = (
        manifest_requires_report_review(manifest)
        if manifest is not None
        else bool(getattr(candidate, "report_review_required", False))
    )
    if not review_required:
        return True
    base_allowed = (
        bool(getattr(candidate, "report_review_required", False))
        and getattr(candidate, "state", None) == "ready_for_report"
        and bool(getattr(candidate, "human_validated", False))
        and getattr(candidate, "report_review_status", None) == "candidate_reviewed"
        and bool(_text(getattr(candidate, "report_reviewer", None)))
    )
    if not base_allowed:
        return False
    review_reference = _text(getattr(candidate, "report_review_reference", None))
    review_sha256 = _text(getattr(candidate, "report_review_sha256", None))
    if not review_reference or not review_sha256:
        return False
    try:
        decision = load_report_review_decision(review_reference)
        return (
            _sha256_file(review_reference) == review_sha256
            and decision.evidence_manifest_sha256
            == getattr(candidate, "evidence_manifest_sha256", None)
            and (
                manifest is None
                or decision.evidence_manifest_sha256 == getattr(manifest, "manifest_sha256", None)
            )
            and decision.reviewer_alias == getattr(candidate, "report_reviewer", None)
        )
    except (OSError, ValueError):
        return False
