from aotp.safety_budget import SafetyBudget


def test_budget_enforces_iterations_requests_and_runtime():
    budget = SafetyBudget(1, 10, 1)
    assert budget.can_continue()
    budget.record(1)
    assert not budget.can_continue()
    assert not SafetyBudget(2, 1, 2).can_continue(elapsed_seconds=1)
