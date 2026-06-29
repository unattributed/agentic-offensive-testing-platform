"""Local human approval queue."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


RISKY_ACTIONS = {
    "active_fuzzing",
    "state_changing_workflow",
    "cross_account_confirmation",
    "account_lockout_risk",
    "possible_valid_vulnerability",
    "report_submission",
}


@dataclass
class ApprovalRequest:
    request_id: str
    action: str
    reason: str
    status: str = "pending"
    created_at_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def approve(self) -> None:
        self.status = "approved"

    def deny(self) -> None:
        self.status = "denied"


def requires_approval(action: str) -> bool:
    return action in RISKY_ACTIONS
