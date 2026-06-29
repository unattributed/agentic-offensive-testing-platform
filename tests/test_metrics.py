from aotp.metrics import OperatorMetrics


def test_metrics_keep_outcomes_and_cost_separate():
    metrics = OperatorMetrics(number_accepted=1, number_duplicate=2, bounty_amount=10, estimated_tool_cost=1)
    assert metrics.number_accepted == 1
    assert metrics.number_duplicate == 2
    assert metrics.bounty_amount - metrics.estimated_tool_cost == 9
