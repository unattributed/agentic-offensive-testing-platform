"""Authorized WSTG authentication boundary planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .objective_generator import WSTGObjective
from .strategy_map import ExecutableFamily


class AuthBoundaryError(ValueError):
    """Raised when an authentication boundary check is unsafe."""


@dataclass(frozen=True)
class AuthBoundaryDecision:
    allowed: bool
    reasons: tuple[str, ...]
    objective_id: str
    wstg_id: str
    evidence_classification: str

    @property
    def summary(self) -> str:
        return "allowed" if self.allowed else "; ".join(self.reasons)

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "objective_id": self.objective_id,
            "wstg_id": self.wstg_id,
            "evidence_classification": self.evidence_classification,
            "summary": self.summary,
        }


def evaluate_auth_boundary_check(
    objective: WSTGObjective,
    *,
    approved: bool,
    approval_reference: str | None,
    authenticated_context: bool,
) -> AuthBoundaryDecision:
    """Gate authentication checks before execution."""

    reasons: list[str] = []
    if objective.family is not ExecutableFamily.AUTH_BOUNDARY:
        reasons.append("objective is not an authentication boundary check")
    if not approved:
        reasons.append("authentication boundary approval is required")
    if not approval_reference or not approval_reference.strip():
        reasons.append("authentication boundary approval reference is required")
    if not authenticated_context:
        reasons.append("authenticated campaign context is required")
    return AuthBoundaryDecision(
        allowed=not reasons,
        reasons=tuple(reasons),
        objective_id=objective.objective_id,
        wstg_id=objective.wstg_id,
        evidence_classification="restricted",
    )
