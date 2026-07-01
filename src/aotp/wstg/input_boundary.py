"""Bounded WSTG input-boundary check planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class InputBoundaryError(ValueError):
    """Raised when input-boundary planning is unsafe."""


class InputPayloadClass(str, Enum):
    METADATA_ONLY = "metadata_only"
    LENGTH_BOUNDARY = "length_boundary"
    ENCODING_BOUNDARY = "encoding_boundary"


@dataclass(frozen=True)
class InputBoundaryPlan:
    objective_id: str
    payload_classes: tuple[InputPayloadClass, ...]
    max_requests: int
    planned_requests: int
    state_changing_denied: bool = True
    evidence_classification: str = "restricted"

    def __post_init__(self) -> None:
        if not self.payload_classes:
            raise InputBoundaryError("at least one payload class is required")
        if self.planned_requests > self.max_requests:
            raise InputBoundaryError("planned input-boundary requests exceed budget")
        if not self.state_changing_denied:
            raise InputBoundaryError("state-changing input-boundary checks require a later sprint approval")

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "payload_classes": [item.value for item in self.payload_classes],
            "max_requests": self.max_requests,
            "planned_requests": self.planned_requests,
            "state_changing_denied": self.state_changing_denied,
            "evidence_classification": self.evidence_classification,
        }


def build_input_boundary_plan(
    objective_id: str,
    *,
    approved_payload_classes: tuple[InputPayloadClass, ...],
    max_requests: int,
) -> InputBoundaryPlan:
    return InputBoundaryPlan(
        objective_id=objective_id,
        payload_classes=approved_payload_classes,
        max_requests=max_requests,
        planned_requests=len(approved_payload_classes),
    )
