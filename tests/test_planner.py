from __future__ import annotations

import pytest

from aotp.planner import (
    PlannerSuggestionError,
    parse_ai_suggestion,
    planner_response_schema,
    request_planning_suggestion,
    validate_ai_suggestion,
)


class StubAdapter:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate(self, task, payload, schema):
        self.calls.append((task, payload, schema))
        return self.result


def test_planner_accepts_only_an_approved_objective_id():
    suggestion = parse_ai_suggestion(
        {"objective_id": "objective-a", "rationale": "First approved item."},
        ["objective-a", "objective-b"],
    )
    assert suggestion.objective_id == "objective-a"


def test_planner_rejects_unknown_objective_id():
    with pytest.raises(PlannerSuggestionError, match="unapproved"):
        parse_ai_suggestion(
            {"objective_id": "objective-c", "rationale": "Not in the campaign."},
            ["objective-a", "objective-b"],
        )


@pytest.mark.parametrize("field", ["action", "authorization", "policy_override", "target"])
def test_planner_rejects_authority_or_execution_fields(field):
    response = {
        "objective_id": "objective-a",
        "rationale": "Attempted expansion.",
        field: True,
    }
    with pytest.raises(PlannerSuggestionError, match="only objective_id"):
        parse_ai_suggestion(response, ["objective-a"])


def test_planner_request_contains_only_approved_ids_and_dynamic_schema():
    adapter = StubAdapter(
        {"objective_id": "objective-b", "rationale": "Approved dependency order."}
    )
    result = request_planning_suggestion(adapter, ["objective-a", "objective-b"])
    assert result.objective_id == "objective-b"
    _task, payload, schema = adapter.calls[0]
    assert payload == {"approved_objective_ids": ["objective-a", "objective-b"]}
    assert schema == planner_response_schema(["objective-a", "objective-b"])
    assert schema["properties"]["objective_id"]["enum"] == ["objective-a", "objective-b"]


def test_legacy_boolean_validator_remains_fail_closed():
    approved = [{"id": "objective-a"}]
    assert validate_ai_suggestion({"id": "objective-a"}, approved)
    assert not validate_ai_suggestion({"id": "objective-b"}, approved)
    assert not validate_ai_suggestion(
        {"id": "objective-a", "authorization": True},
        approved,
    )
