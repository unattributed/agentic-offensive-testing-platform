"""Human approval gate for manual report submission."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .redaction import assert_value_redacted
from .report_package import load_report_package

SCHEMA_VERSION = "1.0"
APPROVED_DECISION = "approved_for_manual_submission"
REJECTED_DECISION = "rejected"
AUTOMATION_REVIEWERS = {
    "automation",
    "automated",
    "bot",
    "ci",
    "ci-bot",
    "system",
}
_ALIAS = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class SubmissionApproval:
    decision_id: str
    report_package_sha256: str
    reviewer_alias: str
    decision: str
    decided_at_utc: str
    rationale: str
    schema_version: str = SCHEMA_VERSION
    decision_sha256: str | None = None

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported submission approval schema")
        if not _ALIAS.fullmatch(self.decision_id):
            raise ValueError("decision_id must be an alias")
        if not _SHA256.fullmatch(self.report_package_sha256):
            raise ValueError("report_package_sha256 must be a SHA256 value")
        reviewer = self.reviewer_alias.strip().lower()
        if (
            not _ALIAS.fullmatch(reviewer)
            or reviewer in AUTOMATION_REVIEWERS
            or reviewer.endswith("-bot")
            or reviewer.endswith("_bot")
        ):
            raise ValueError("manual submission approval requires a named human reviewer")
        if self.decision not in {APPROVED_DECISION, REJECTED_DECISION}:
            raise ValueError("submission approval decision is unsupported")
        try:
            decided_at = datetime.fromisoformat(
                self.decided_at_utc.replace("Z", "+00:00")
            )
        except (AttributeError, ValueError) as exc:
            raise ValueError("decided_at_utc is invalid") from exc
        if decided_at.tzinfo is None:
            raise ValueError("decided_at_utc must include a timezone")
        if not isinstance(self.rationale, str) or not self.rationale.strip():
            raise ValueError("submission approval rationale is required")
        assert_value_redacted(asdict(self))
        if self.decision_sha256 is not None and self.decision_sha256 != approval_digest(
            self
        ):
            raise ValueError("submission approval integrity check failed")


@dataclass(frozen=True)
class SubmissionGateDecision:
    allowed: bool
    status: str
    reason: str


def approval_digest(approval: SubmissionApproval) -> str:
    payload = asdict(approval)
    payload["decision_sha256"] = None
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def evaluate_submission_gate(
    report_package_path: str | Path,
    approval: SubmissionApproval | None,
) -> SubmissionGateDecision:
    package = load_report_package(report_package_path)
    if approval is None:
        return SubmissionGateDecision(
            False,
            "pending_human_review",
            "manual submission requires an explicit human approval record",
        )
    approval.validate()
    if approval.report_package_sha256 != package.package_sha256:
        return SubmissionGateDecision(
            False,
            "denied",
            "submission approval does not match the report package",
        )
    if approval.decision != APPROVED_DECISION:
        return SubmissionGateDecision(
            False,
            "denied",
            "human reviewer rejected manual submission",
        )
    return SubmissionGateDecision(
        True,
        "approved_for_manual_submission",
        "human approval permits manual operator submission only",
    )


def write_submission_approval(
    approval: SubmissionApproval, path: str | Path
) -> Path:
    approval.decision_sha256 = None
    approval.validate()
    approval.decision_sha256 = approval_digest(approval)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".submission-approval.", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(asdict(approval), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
        os.chmod(output, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def load_submission_approval(path: str | Path) -> SubmissionApproval:
    try:
        data: Any = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("approval root must be a mapping")
        approval = SubmissionApproval(**data)
        approval.validate()
        return approval
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"submission approval is invalid: {path}: {exc}") from exc
