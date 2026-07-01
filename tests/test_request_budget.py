from aotp.request_budget import RequestBudget
from aotp.tool_risk_tiers import ToolRiskTier


def test_request_budget_denies_before_mutating_total():
    budget = RequestBudget(max_requests=1)
    decision = budget.check(tool_name="http_metadata", risk_tier=ToolRiskTier.PASSIVE_METADATA, request_count=2)
    assert not decision.allowed
    assert budget.used_requests == 0


def test_request_budget_consumes_allowed_calls():
    budget = RequestBudget(max_requests=3, per_tool_limits={"http_metadata": 2})
    assert budget.consume(tool_name="http_metadata", risk_tier="passive_metadata", request_count=1).allowed
    assert budget.consume(tool_name="http_metadata", risk_tier="passive_metadata", request_count=1).allowed
    denied = budget.consume(tool_name="http_metadata", risk_tier="passive_metadata", request_count=1)
    assert not denied.allowed
    assert budget.used_requests == 2
    assert budget.used_by_tool["http_metadata"] == 2


def test_request_budget_enforces_risk_tier_limits():
    budget = RequestBudget(
        max_requests=10,
        per_risk_tier_limits={ToolRiskTier.PASSIVE_SCANNER: 1},
    )
    assert budget.consume(tool_name="zap_passive_baseline", risk_tier="passive_scanner", request_count=1).allowed
    denied = budget.consume(tool_name="zap_passive_baseline", risk_tier="passive_scanner", request_count=1)
    assert not denied.allowed
    assert denied.summary == "risk-tier request budget exceeded"
