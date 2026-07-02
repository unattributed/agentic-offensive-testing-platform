"""Evidence-driven proof request models for agentic campaign loops."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from aotp.wstg import WSTGEnginePlan


class ProofRequestError(ValueError):
    """Raised when a proof request is malformed."""


@dataclass(frozen=True)
class ProofRequest:
    """A request for missing evidence before a finding can be validated."""

    proof_request_id: str
    objective_id: str
    wstg_id: str
    reason: str
    missing_evidence: tuple[str, ...]
    requested_agent: str
    status: str = "needs_more_evidence"

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", self.proof_request_id) is None:
            raise ProofRequestError("proof_request_id must be a safe lowercase identifier")
        if not self.objective_id.strip() or not self.wstg_id.strip():
            raise ProofRequestError("objective_id and wstg_id are required")
        if not self.reason.strip() or not self.requested_agent.strip():
            raise ProofRequestError("proof request reason and requested agent are required")
        if not self.missing_evidence:
            raise ProofRequestError("missing evidence list is required")
        if self.status not in {"needs_more_evidence", "needs_human_approval", "blocked"}:
            raise ProofRequestError("unsupported proof request status")

    def as_dict(self) -> dict[str, Any]:
        return {
            "proof_request_id": self.proof_request_id,
            "objective_id": self.objective_id,
            "wstg_id": self.wstg_id,
            "reason": self.reason,
            "missing_evidence": list(self.missing_evidence),
            "requested_agent": self.requested_agent,
            "status": self.status,
        }


def build_proof_requests(plan: WSTGEnginePlan, observed_wstg_ids: Iterable[str], *, limit: int = 20) -> tuple[ProofRequest, ...]:
    """Create bounded proof requests for ready objectives without supporting evidence."""

    observed = set(observed_wstg_ids)
    requests: list[ProofRequest] = []
    for item in plan.ready_tests:
        if len(requests) >= limit:
            break
        if item.wstg_id in observed:
            continue
        requests.append(
            ProofRequest(
                proof_request_id=f"proof-{item.wstg_id.lower().replace('-', '-')}",
                objective_id=item.objective_id,
                wstg_id=item.wstg_id,
                reason="ready WSTG objective has not yet been supported by evidence in this campaign loop",
                missing_evidence=tuple(item.test_case.evidence_required),
                requested_agent=_agent_for_wstg_id(item.wstg_id),
            )
        )
    return tuple(requests)


def _agent_for_wstg_id(wstg_id: str) -> str:
    if "-CLNT-" in wstg_id:
        return "browser-workflow-agent"
    if "-APIT-" in wstg_id:
        return "api-discovery-agent"
    if "-ATHN-" in wstg_id or "-SESS-" in wstg_id or "-ATHZ-" in wstg_id:
        return "authenticated-workflow-agent"
    if "-INPV-" in wstg_id or "-BUSL-" in wstg_id:
        return "validation-agent"
    return "campaign-lead-agent"
