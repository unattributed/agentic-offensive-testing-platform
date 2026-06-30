from __future__ import annotations

from copy import deepcopy

import pytest

from aotp.capability_registry import module_summary
from aotp.config import load_yaml
from aotp.control_panel import (
    PANEL_SAFE_OBSERVATIONS,
    build_panel_dry_run_observation_plan,
    unsafe_panel_observations,
)
from aotp.executor import execute
from aotp.policy_gate import evaluate


def _safe_observation_scope(example_scope: dict) -> dict:
    scope = deepcopy(example_scope)
    scope["service_control_panels"] = {
        "authorized": True,
        "panels": [
            {
                "alias": "example-admin-panel",
                "target_alias": "local-placeholder",
                "panel_type": "admin_panel",
                "exposure": "placeholder_only",
                "approved_actions": ["plan_panel_target_metadata", "plan_safe_panel_observations"],
                "denied_actions": [
                    "brute_force",
                    "credential_attack",
                    "credential_guessing",
                    "credential_stuffing",
                    "default_password_check",
                    "destructive_action",
                    "destructive_panel_action",
                    "login_attempt",
                    "lockout_triggering",
                    "panel_crawl",
                    "password_spraying",
                    "session_hijacking",
                    "token_replay",
                    "unsafe_crawling",
                ],
            }
        ],
    }
    return scope


def _safe_observation_objective() -> dict:
    return {
        "id": "control-panel-safe-observations",
        "target_alias": "local-placeholder",
        "category": "service_control_panel",
        "module": "service_control_panel",
        "panel_alias": "example-admin-panel",
        "panel_type": "admin_panel",
        "action": "plan_safe_panel_observations",
        "service": "https",
        "environment": "isolated-example-environment",
        "requested_observations": [
            "response_header_metadata",
            "tls_configuration_metadata",
            "login_exposure_metadata",
            "version_banner_metadata",
            "default_page_metadata",
            "indexing_metadata",
        ],
    }


def test_safe_observation_plan_is_deterministic_and_network_silent():
    objective = _safe_observation_objective()
    plan = build_panel_dry_run_observation_plan(objective)

    assert plan["panel_alias"] == "example-admin-panel"
    assert plan["network_silent"] is True
    assert plan["request_count"] == 0
    assert plan["credential_material"] == "not_collected"
    assert plan["screenshots"] == []
    assert plan["captures"] == []
    assert plan["finding_claims"] == []
    assert [item["observation_id"] for item in plan["planned_observations"]] == objective[
        "requested_observations"
    ]
    assert {item["execution"] for item in plan["planned_observations"]} == {"not_executed"}


def test_policy_allows_safe_panel_observation_dry_run(example_scope, tmp_path):
    decision = evaluate(
        _safe_observation_scope(example_scope),
        _safe_observation_objective(),
        workspace=tmp_path,
    )
    assert decision.allowed, decision.reasons


def test_executor_returns_safe_panel_observation_metadata():
    result = execute(_safe_observation_objective(), live=False)

    assert result.tool == "control-panel-dry-run-planner"
    assert result.request_count == 0
    assert "no network request was sent" in result.response_metadata["status"]
    plan = result.response_metadata["observation_plan"]
    assert plan["network_silent"] is True
    assert len(plan["planned_observations"]) == 6


def test_unapproved_panel_action_is_denied(example_scope, tmp_path):
    objective = _safe_observation_objective()
    objective["action"] = "enumerate_panel_users"
    decision = evaluate(_safe_observation_scope(example_scope), objective, workspace=tmp_path)

    assert not decision.allowed
    assert "panel action is not explicitly approved: enumerate_panel_users" in decision.reasons


def test_unsupported_panel_observation_is_denied(example_scope, tmp_path):
    objective = _safe_observation_objective()
    objective["requested_observations"].append("active_crawl")
    decision = evaluate(_safe_observation_scope(example_scope), objective, workspace=tmp_path)

    assert not decision.allowed
    assert "panel observation is not approved as safe: active_crawl" in decision.reasons


def test_missing_panel_observations_are_denied_before_execution(example_scope, tmp_path):
    objective = _safe_observation_objective()
    objective.pop("requested_observations")
    decision = evaluate(_safe_observation_scope(example_scope), objective, workspace=tmp_path)
    assert not decision.allowed
    assert "safe panel observation planning requires requested_observations" in decision.reasons
    with pytest.raises(ValueError, match="requires requested_observations"):
        build_panel_dry_run_observation_plan(objective)


def test_default_password_and_login_checks_are_not_safe_observations():
    objective = {
        "requested_observations": [
            "response_header_metadata",
            "default_password_check",
            "login_attempt",
        ]
    }

    assert unsafe_panel_observations(objective) == ("default_password_check", "login_attempt")


def test_safe_observation_case_fixture_has_no_runtime_actions(project_root):
    case = load_yaml(project_root / "cases/control-panel-safe-observations.example.yaml").data
    assert set(case["requested_observations"]) == PANEL_SAFE_OBSERVATIONS
    assert case["approved_actions"] == ["plan_safe_panel_observations"]
    assert "login_attempt" not in case["approved_actions"]
    assert "default_password_check" not in case["requested_observations"]
    assert "panel_crawl" not in case["requested_observations"]


def test_capability_summary_lists_control_panel_safe_observations():
    modules = {module["module_id"]: module for module in module_summary()["modules"]}
    panel_module = modules["service_control_panel"]

    assert panel_module["network_silent_default"] is True
    assert set(panel_module["supported_capabilities"]) == PANEL_SAFE_OBSERVATIONS
    assert "credential_guessing" in panel_module["denied_actions"]
