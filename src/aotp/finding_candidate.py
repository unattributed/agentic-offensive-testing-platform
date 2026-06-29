"""Evidence-bound finding candidate model."""

from __future__ import annotations

from dataclasses import dataclass


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


@dataclass
class FindingCandidate:
    finding_id: str
    evidence_reference: str
    state: str = "observed"
    severity_candidate: str = "unrated"
    confidence: str = "low"
    evidence_strength: str = "weak"
    human_validated: bool = False

    def validate(self) -> None:
        if self.state not in FINDING_STATES:
            raise ValueError("unsupported finding state")
        if not self.evidence_reference:
            raise ValueError("finding candidate requires evidence")
        if self.state in {"confirmed", "ready_for_report"} and not self.human_validated:
            raise ValueError("confirmed findings require human validation")
