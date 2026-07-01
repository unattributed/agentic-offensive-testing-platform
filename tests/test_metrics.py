from __future__ import annotations

import json
import os

import pytest

from aotp.metrics import (
    OperatorMetrics,
    load_operator_metrics,
    write_operator_metrics,
)


def _metrics(**changes):
    values = {
        "measurement_period_start_utc": "2026-07-01T00:00:00Z",
        "measurement_period_end_utc": "2026-07-02T00:00:00Z",
        "manual_hours_spent": 2.5,
        "agent_assisted_hours_spent": 1.0,
        "number_of_requests": 5,
        "number_of_cases_executed": 4,
        "number_of_candidates_generated": 3,
        "number_confirmed": 2,
        "number_submitted": 2,
        "number_accepted": 1,
        "number_rejected": 0,
        "number_duplicate": 1,
        "bounty_amount": 100,
        "estimated_tool_cost": 4.5,
    }
    values.update(changes)
    return OperatorMetrics(**values)


def test_operator_metrics_round_trip_as_private_aggregate(tmp_path):
    metrics = _metrics()
    path = write_operator_metrics(metrics, tmp_path / "operator-metrics.json")

    assert load_operator_metrics(path) == metrics
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_metrics_keep_time_counts_outcomes_bounty_and_cost_separate():
    payload = json.loads(json.dumps(_metrics().__dict__))

    assert payload["manual_hours_spent"] == 2.5
    assert payload["number_accepted"] == 1
    assert payload["bounty_amount"] == 100
    assert payload["estimated_tool_cost"] == 4.5
    assert not any(
        term in key
        for key in payload
        for term in ("target", "asset", "program", "evidence", "finding")
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("manual_hours_spent", -1),
        ("bounty_amount", float("inf")),
        ("number_of_requests", 1.5),
    ),
)
def test_operator_metrics_reject_invalid_numeric_values(field, value):
    with pytest.raises(ValueError):
        _metrics(**{field: value}).validate()


@pytest.mark.parametrize(
    "changes",
    (
        {"number_confirmed": 4},
        {"number_submitted": 3},
        {"number_accepted": 2, "number_duplicate": 1},
    ),
)
def test_operator_metrics_reject_impossible_outcome_counts(changes):
    with pytest.raises(ValueError):
        _metrics(**changes).validate()
