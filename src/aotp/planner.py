"""Deterministic planner. AI output is advisory only."""

from __future__ import annotations

from typing import Any


def next_objective(pending: list[dict[str, Any]]) -> dict[str, Any] | None:
    return pending[0] if pending else None


def validate_ai_suggestion(suggestion: dict[str, Any], approved: list[dict[str, Any]]) -> bool:
    suggested_id = suggestion.get("id")
    return any(item.get("id") == suggested_id for item in approved)
