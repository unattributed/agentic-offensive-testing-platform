"""Generic WSTG live campaign state models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_ALLOWED_DECISION_STATUSES = {"planned", "started", "completed", "blocked", "denied", "observed_error"}
_ALLOWED_FINDING_STATES = {
    "observed",
    "candidate",
    "needs_more_evidence",
    "needs_human_approval",
    "validated",
    "rejected_false_positive",
    "duplicate",
    "out_of_scope",
    "report_ready",
}


class CampaignStateError(ValueError):
    """Raised when generic campaign state is unsafe or inconsistent."""


@dataclass(frozen=True)
class CampaignDecision:
    """One auditable agent decision in a campaign loop."""

    step: int
    agent: str
    action: str
    reason: str
    status: str
    wstg_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.step < 1:
            raise CampaignStateError("decision step must be positive")
        if not self.agent.strip() or not self.action.strip() or not self.reason.strip():
            raise CampaignStateError("decision agent, action, and reason are required")
        if self.status not in _ALLOWED_DECISION_STATUSES:
            raise CampaignStateError("unsupported decision status")

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "agent": self.agent,
            "action": self.action,
            "reason": self.reason,
            "status": self.status,
            "wstg_ids": list(self.wstg_ids),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class CampaignFinding:
    """Evidence-bound generic finding candidate state."""

    finding_id: str
    title: str
    state: str
    severity: str
    confidence: str
    wstg_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    rationale: str
    next_step: str

    def __post_init__(self) -> None:
        if not self.finding_id.strip() or not self.title.strip():
            raise CampaignStateError("finding id and title are required")
        if self.state not in _ALLOWED_FINDING_STATES:
            raise CampaignStateError("unsupported finding lifecycle state")
        if self.state in {"candidate", "validated", "report_ready"} and not self.evidence_refs:
            raise CampaignStateError("candidate, validated, and report-ready findings require evidence")
        if not self.rationale.strip() or not self.next_step.strip():
            raise CampaignStateError("finding rationale and next step are required")

    def as_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "state": self.state,
            "severity": self.severity,
            "confidence": self.confidence,
            "wstg_ids": list(self.wstg_ids),
            "evidence_refs": list(self.evidence_refs),
            "rationale": self.rationale,
            "next_step": self.next_step,
        }


@dataclass
class WSTGLiveCampaignState:
    """Mutable state for one generic WSTG live campaign."""

    campaign_id: str
    target_alias: str
    base_url: str
    planned_objectives: int
    queued_actions: int = 0
    executed_actions: int = 0
    observed_wstg_ids: set[str] = field(default_factory=set)
    decisions: list[CampaignDecision] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)
    proof_request_ids: list[str] = field(default_factory=list)

    def record_decision(self, decision: CampaignDecision) -> None:
        self.decisions.append(decision)

    def mark_observed(self, wstg_ids: tuple[str, ...]) -> None:
        self.observed_wstg_ids.update(wstg_ids)

    def as_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "target_alias": self.target_alias,
            "base_url": self.base_url,
            "planned_objectives": self.planned_objectives,
            "queued_actions": self.queued_actions,
            "executed_actions": self.executed_actions,
            "observed_wstg_ids": sorted(self.observed_wstg_ids),
            "decisions": [decision.as_dict() for decision in self.decisions],
            "finding_ids": list(self.finding_ids),
            "proof_request_ids": list(self.proof_request_ids),
        }
