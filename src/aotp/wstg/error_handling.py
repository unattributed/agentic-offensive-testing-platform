"""Bounded WSTG error-handling check planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ErrorHandlingPlanError(ValueError):
    """Raised when error-handling boundaries are unsafe."""


@dataclass(frozen=True)
class ErrorHandlingPlan:
    objective_id: str
    max_requests: int
    planned_requests: int
    stop_conditions: tuple[str, ...]
    evidence_classification: str = "restricted"

    def __post_init__(self) -> None:
        if self.max_requests < 0 or self.planned_requests < 0:
            raise ErrorHandlingPlanError("request counts must be non-negative")
        if self.planned_requests > self.max_requests:
            raise ErrorHandlingPlanError("planned error-handling requests exceed budget")
        if not self.stop_conditions:
            raise ErrorHandlingPlanError("error-handling plans require stop conditions")

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "max_requests": self.max_requests,
            "planned_requests": self.planned_requests,
            "stop_conditions": list(self.stop_conditions),
            "evidence_classification": self.evidence_classification,
        }


def build_error_handling_plan(
    objective_id: str,
    *,
    max_requests: int,
    planned_requests: int = 1,
) -> ErrorHandlingPlan:
    return ErrorHandlingPlan(
        objective_id=objective_id,
        max_requests=max_requests,
        planned_requests=planned_requests,
        stop_conditions=(
            "unexpected_5xx_burst",
            "stack_trace_observed",
            "lockout_or_instability_signal",
        ),
    )
