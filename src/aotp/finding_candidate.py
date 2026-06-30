"""Persisted evidence-bound finding candidate model."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .evidence import load_manifest, sha256_file
from .redaction import assert_value_redacted
from .report_review import REVIEW_STATUSES, evaluate_report_review_gate, report_inclusion_allowed
from .verifier import Verdict, load_verification


FINDING_STATES = (
    "observed",
    "candidate",
    "needs_reproduction",
    "needs_human_review",
    "confirmed",
    "duplicate_risk",
    "out_of_scope",
    "not_security_impacting",
    "ready_for_report",
    "submitted_manually",
    "accepted",
    "rejected",
    "paid",
)

SEVERITIES = {"unrated", "informational", "low", "medium", "high", "critical"}
CONFIDENCES = {"low", "medium", "high"}
EVIDENCE_STRENGTHS = {"weak", "medium", "strong"}


@dataclass
class FindingCandidate:
    finding_id: str
    evidence_reference: str
    state: str = "observed"
    severity_candidate: str = "unrated"
    confidence: str = "low"
    evidence_strength: str = "weak"
    human_validated: bool = False
    report_review_required: bool = False
    report_review_status: str = "not_required"
    report_reviewer: str | None = None
    title: str = "Unreviewed observation"
    summary: str = "Evidence requires review."
    evidence_manifest_sha256: str | None = None
    verification_reference: str | None = None
    verification_sha256: str | None = None
    target_alias: str | None = None
    case_id: str | None = None
    fingerprint: str | None = None
    created_at_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    lifecycle_history: list[dict[str, str]] = field(default_factory=list)
    schema_version: str = "1.0"
    candidate_sha256: str | None = None

    def validate(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported finding candidate schema")
        if self.state not in FINDING_STATES:
            raise ValueError("unsupported finding state")
        if not self.evidence_reference:
            raise ValueError("finding candidate requires evidence")
        if self.severity_candidate not in SEVERITIES:
            raise ValueError("unsupported severity candidate")
        if self.confidence not in CONFIDENCES:
            raise ValueError("unsupported finding confidence")
        if self.evidence_strength not in EVIDENCE_STRENGTHS:
            raise ValueError("unsupported evidence strength")
        if self.report_review_status not in REVIEW_STATUSES:
            raise ValueError("unsupported report review status")
        if self.report_review_required:
            if self.report_review_status != "candidate_reviewed":
                raise ValueError("panel evidence requires completed report review")
            if not self.report_reviewer:
                raise ValueError("panel evidence requires a report reviewer")
        if self.state != "observed":
            for name, value in (
                ("evidence manifest hash", self.evidence_manifest_sha256),
                ("verification reference", self.verification_reference),
                ("verification hash", self.verification_sha256),
                ("fingerprint", self.fingerprint),
            ):
                if not value:
                    raise ValueError(f"finding candidate requires {name}")
        if self.state in {"confirmed", "ready_for_report"} and not self.human_validated:
            raise ValueError("confirmed findings require human validation")
        if self.state == "ready_for_report" and (
            self.severity_candidate == "unrated" or self.evidence_strength == "weak"
        ):
            raise ValueError("report-ready findings require rated severity and stronger evidence")
        if self.state == "ready_for_report" and not report_inclusion_allowed(self):
            raise ValueError("report-ready findings require completed report review")
        assert_value_redacted(asdict(self))
        if self.candidate_sha256 is not None and self.candidate_sha256 != candidate_digest(self):
            raise ValueError("finding candidate integrity check failed")


def candidate_digest(candidate: FindingCandidate) -> str:
    payload = asdict(candidate)
    payload["candidate_sha256"] = None
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def create_candidate(
    evidence_path: str | Path,
    verification_path: str | Path,
    *,
    finding_id: str,
    title: str,
    summary: str,
    severity_candidate: str = "unrated",
    evidence_strength: str = "weak",
    report_reviewed: bool = False,
    reviewer: str = "system",
) -> FindingCandidate:
    manifest = load_manifest(evidence_path)
    verification = load_verification(verification_path)
    if verification.evidence_manifest_sha256 != manifest.manifest_sha256:
        raise ValueError("verification does not reference the supplied evidence manifest")
    if verification.verdict != Verdict.FAIL:
        raise ValueError("only a fail verdict can create a finding candidate")
    review_gate = evaluate_report_review_gate(
        manifest,
        report_reviewed=report_reviewed,
        reviewer=reviewer,
    )
    if not review_gate.allowed:
        raise ValueError(review_gate.reason)
    fingerprint_source = "|".join(
        [
            manifest.sponsor_alias,
            manifest.target_alias,
            manifest.case_id,
            verification.evidence_manifest_sha256,
        ]
    )
    now = datetime.now(UTC).isoformat()
    candidate = FindingCandidate(
        finding_id=finding_id,
        evidence_reference=str(evidence_path),
        state="candidate",
        severity_candidate=severity_candidate,
        confidence=verification.confidence,
        evidence_strength=evidence_strength,
        title=title,
        summary=summary,
        report_review_required=review_gate.review_required,
        report_review_status=review_gate.status,
        report_reviewer=review_gate.reviewer,
        evidence_manifest_sha256=manifest.manifest_sha256,
        verification_reference=str(verification_path),
        verification_sha256=sha256_file(verification_path),
        target_alias=manifest.target_alias,
        case_id=manifest.case_id,
        fingerprint=hashlib.sha256(fingerprint_source.encode()).hexdigest(),
        created_at_utc=now,
        updated_at_utc=now,
        lifecycle_history=[
            {
                "timestamp_utc": now,
                "from": "none",
                "to": "candidate",
                "reviewer": review_gate.reviewer or "system",
            }
        ],
    )
    candidate.validate()
    return candidate


def write_candidate(candidate: FindingCandidate, path: str | Path) -> Path:
    candidate.candidate_sha256 = None
    candidate.validate()
    candidate.candidate_sha256 = candidate_digest(candidate)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".finding.", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(asdict(candidate), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
        os.chmod(output, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def load_candidate(path: str | Path) -> FindingCandidate:
    try:
        candidate = FindingCandidate(**json.loads(Path(path).read_text(encoding="utf-8")))
        candidate.validate()
        return candidate
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"finding candidate is invalid: {path}: {exc}") from exc
