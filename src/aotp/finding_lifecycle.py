"""Conservative finding lifecycle transitions."""

from __future__ import annotations

from .finding_candidate import FINDING_STATES, FindingCandidate


ALLOWED_TRANSITIONS = {
    "observed": {"candidate", "out_of_scope", "not_security_impacting"},
    "candidate": {"needs_reproduction", "needs_human_review", "duplicate_risk"},
    "needs_reproduction": {"candidate", "needs_human_review", "not_security_impacting"},
    "needs_human_review": {"confirmed", "duplicate_risk", "out_of_scope", "not_security_impacting"},
    "confirmed": {"ready_for_report"},
    "ready_for_report": {"submitted_manually"},
    "submitted_manually": {"accepted", "rejected", "duplicate_risk"},
    "accepted": {"paid"},
}


def transition(finding: FindingCandidate, new_state: str, *, human_validated: bool = False) -> None:
    if new_state not in FINDING_STATES:
        raise ValueError("unsupported finding state")
    if new_state not in ALLOWED_TRANSITIONS.get(finding.state, set()):
        raise ValueError(f"transition from {finding.state} to {new_state} is not allowed")
    finding.state = new_state
    finding.human_validated = finding.human_validated or human_validated
    finding.validate()
