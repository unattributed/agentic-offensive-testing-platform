"""Deterministic planning with schema-bound advisory model suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class PlannerSuggestionError(ValueError):
    """Raised when advisory output exceeds the approved objective boundary."""


@dataclass(frozen=True)
class PlannerSuggestion:
    objective_id: str
    rationale: str


def next_objective(pending: list[dict[str, Any]]) -> dict[str, Any] | None:
    return pending[0] if pending else None


def planner_response_schema(approved_objective_ids: list[str]) -> dict[str, Any]:
    approved = _approved_ids(approved_objective_ids)
    return {
        "type": "object",
        "properties": {
            "objective_id": {"type": "string", "enum": list(approved)},
            "rationale": {"type": "string"},
        },
        "required": ["objective_id", "rationale"],
        "additionalProperties": False,
    }


def _approved_ids(values: list[str]) -> tuple[str, ...]:
    if (
        not values
        or any(not isinstance(value, str) or not value.strip() for value in values)
        or len(values) != len(set(values))
    ):
        raise PlannerSuggestionError("approved objective IDs must be unique non-empty text")
    return tuple(values)


def parse_ai_suggestion(
    suggestion: dict[str, Any],
    approved_objective_ids: list[str],
) -> PlannerSuggestion:
    approved = _approved_ids(approved_objective_ids)
    if not isinstance(suggestion, dict) or set(suggestion) != {"objective_id", "rationale"}:
        raise PlannerSuggestionError(
            "model suggestion must contain only objective_id and rationale"
        )
    objective_id = suggestion.get("objective_id")
    rationale = suggestion.get("rationale")
    if objective_id not in approved:
        raise PlannerSuggestionError("model suggested an unapproved objective ID")
    if not isinstance(rationale, str) or not rationale.strip():
        raise PlannerSuggestionError("model suggestion rationale must be non-empty text")
    return PlannerSuggestion(objective_id=str(objective_id), rationale=rationale.strip())


def validate_ai_suggestion(suggestion: dict[str, Any], approved: list[dict[str, Any]]) -> bool:
    approved_ids = [
        item["id"]
        for item in approved
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    normalized = {
        "objective_id": suggestion.get("objective_id", suggestion.get("id")),
        "rationale": suggestion.get("rationale", "advisory suggestion"),
    }
    if set(suggestion) - {"id", "objective_id", "rationale"}:
        return False
    try:
        parse_ai_suggestion(normalized, approved_ids)
    except PlannerSuggestionError:
        return False
    return True


def request_planning_suggestion(
    adapter: Any,
    approved_objective_ids: list[str],
) -> PlannerSuggestion:
    approved = list(_approved_ids(approved_objective_ids))
    result = adapter.generate(
        "Suggest one objective ID from the approved list. This is advisory only.",
        {"approved_objective_ids": approved},
        planner_response_schema(approved),
    )
    return parse_ai_suggestion(result, approved)
