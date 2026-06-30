import pytest

from aotp.safety_budget import SafetyBudget


def test_budget_enforces_iterations_requests_and_runtime():
    budget = SafetyBudget(1, 10, 1, 1, 1)
    assert budget.can_continue()
    budget.record(1)
    assert not budget.can_continue()
    assert not SafetyBudget(2, 1, 2, 2, 1).can_continue(elapsed_seconds=1)


def test_budget_denies_proposed_request_before_execution():
    budget = SafetyBudget(2, 10, 3, 2, 2, requests=1, current_minute_requests=1)
    assert budget.denial_reason(elapsed_seconds=0, proposed_requests=2) == "rate_limit"
    budget.reset_rate_window()
    assert budget.denial_reason(elapsed_seconds=0, proposed_requests=2) is None
    budget.record(2, failed=True)
    assert budget.requests == 3
    assert budget.consecutive_failures == 1


def test_budget_stops_after_consecutive_failure_limit():
    budget = SafetyBudget(5, 10, 5, 5, 2)
    budget.record(0, failed=True)
    budget.record(0, failed=True)
    assert budget.denial_reason(elapsed_seconds=0) == "consecutive_failure_limit"


def test_budget_rejects_negative_request_counts():
    budget = SafetyBudget(1, 1, 1, 1, 1)
    with pytest.raises(ValueError, match="cannot be negative"):
        budget.record(-1)
