from __future__ import annotations

import pytest

from aotp.campaigns.execution_planner import CampaignAction, ExecutionPlannerError, plan_campaign_actions
from aotp.campaigns.target_runtime import build_juice_shop_target_runtime
from aotp.wstg import build_wstg_engine_plan


def test_execution_planner_creates_read_only_same_origin_actions() -> None:
    runtime = build_juice_shop_target_runtime(max_actions=4, max_ready_tests=20)
    plan = build_wstg_engine_plan(runtime.build_wstg_profile(campaign_id="local-juice-shop-generic", max_ready_tests=20))
    execution_plan = plan_campaign_actions(plan, runtime)

    assert len(execution_plan.actions) == 4
    assert execution_plan.actions[0].method == "GET"
    assert execution_plan.actions[0].path == "/"
    assert execution_plan.actions[0].tool_name == "http_metadata"
    assert all(action.state_changing is False for action in execution_plan.actions)
    assert all(action.requires_human_approval is False for action in execution_plan.actions)
    assert any(blocked["disposition"] in {"deferred", "denied"} for blocked in execution_plan.blocked_objectives)


def test_execution_planner_rejects_state_changing_action() -> None:
    with pytest.raises(ExecutionPlannerError):
        CampaignAction(
            action_id="bad-action",
            action_type="http_get",
            tool_name="http_metadata",
            method="POST",
            path="/",
            wstg_ids=("WSTG-v42-INFO-06",),
            objective_ids=(),
            reason="invalid method",
        )


def test_execution_planner_preserves_observable_api_wstg_mapping_when_api_objective_is_deferred() -> None:
    runtime = build_juice_shop_target_runtime(max_actions=5, max_ready_tests=15)
    plan = build_wstg_engine_plan(runtime.build_wstg_profile(campaign_id="local-juice-shop-generic", max_ready_tests=15))
    execution_plan = plan_campaign_actions(plan, runtime)

    api_action = next(action for action in execution_plan.actions if action.path == "/api/Products")
    assert "WSTG-v42-APIT-01" in api_action.wstg_ids
    assert "WSTG-v42-INFO-06" in api_action.wstg_ids
    assert all(objective_id.startswith("local-juice-shop-generic:") for objective_id in api_action.objective_ids)
