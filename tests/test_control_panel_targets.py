from __future__ import annotations

from copy import deepcopy

import pytest

from aotp.capability_registry import module_summary
from aotp.config import ConfigError, parse_scope
from aotp.control_panel import PANEL_TYPES, PANEL_UNSAFE_ACTIONS
from aotp.executor import execute
from aotp.policy_gate import evaluate


def _panel_scope(example_scope: dict) -> dict:
    scope = deepcopy(example_scope)
    scope["service_control_panels"] = {
        "authorized": True,
        "panels": [
            {
                "alias": "example-admin-panel",
                "target_alias": "local-placeholder",
                "panel_type": "admin_panel",
                "exposure": "placeholder_only",
                "approved_actions": ["plan_panel_target_metadata"],
                "denied_actions": sorted(PANEL_UNSAFE_ACTIONS),
            }
        ],
    }
    return scope


def _panel_objective() -> dict:
    return {
        "id": "control-panel-target-model",
        "target_alias": "local-placeholder",
        "category": "service_control_panel",
        "module": "service_control_panel",
        "panel_alias": "example-admin-panel",
        "panel_type": "admin_panel",
        "action": "plan_panel_target_metadata",
        "service": "https",
        "environment": "isolated-example-environment",
    }


def test_panel_scope_parses_explicit_alias(example_scope):
    scope = _panel_scope(example_scope)
    parsed = parse_scope(scope)
    panel = parsed.panel("example-admin-panel")
    assert panel is not None
    assert panel.alias == "example-admin-panel"
    assert panel.target_alias == "local-placeholder"
    assert panel.panel_type == "admin_panel"
    assert panel.approved_actions == ("plan_panel_target_metadata",)


def test_panel_scope_rejects_unknown_panel_type(example_scope):
    scope = _panel_scope(example_scope)
    scope["service_control_panels"]["panels"][0]["panel_type"] = "database_admin"
    with pytest.raises(ConfigError, match="unsupported panel_type"):
        parse_scope(scope)


def test_panel_scope_rejects_unknown_target_reference(example_scope):
    scope = _panel_scope(example_scope)
    scope["service_control_panels"]["panels"][0]["target_alias"] = "outside-scope"
    with pytest.raises(ConfigError, match="must reference allowed_targets"):
        parse_scope(scope)


def test_panel_scope_rejects_overlapping_approved_and_denied_actions(example_scope):
    scope = _panel_scope(example_scope)
    scope["service_control_panels"]["panels"][0]["denied_actions"].append(
        "plan_panel_target_metadata"
    )
    with pytest.raises(ConfigError, match="overlap"):
        parse_scope(scope)


def test_listed_panel_alias_allows_dry_run_planning(example_scope, tmp_path):
    objective = _panel_objective()
    decision = evaluate(_panel_scope(example_scope), objective, workspace=tmp_path)
    assert decision.allowed, decision.reasons

    result = execute(objective, live=False)
    assert result.tool == "deterministic-dry-run"
    assert result.request_count == 0
    assert "no network request was sent" in result.response_metadata["status"]


def test_unlisted_panel_alias_is_denied(example_scope, tmp_path):
    objective = _panel_objective()
    objective["panel_alias"] = "unlisted-panel"
    decision = evaluate(_panel_scope(example_scope), objective, workspace=tmp_path)
    assert not decision.allowed
    assert "panel alias is not explicitly allowlisted" in decision.reasons


def test_missing_panel_alias_is_denied(example_scope, tmp_path):
    objective = _panel_objective()
    objective.pop("panel_alias")
    decision = evaluate(_panel_scope(example_scope), objective, workspace=tmp_path)
    assert not decision.allowed
    assert "panel alias is missing" in decision.reasons


def test_panel_alias_must_match_target_alias(example_scope, tmp_path):
    objective = _panel_objective()
    objective["target_alias"] = "outside-scope"
    decision = evaluate(_panel_scope(example_scope), objective, workspace=tmp_path)
    assert not decision.allowed
    assert "target is not explicitly allowlisted" in decision.reasons
    assert "panel target alias does not match objective" in decision.reasons


def test_panel_type_is_required_and_must_match_scope(example_scope, tmp_path):
    missing = _panel_objective()
    missing.pop("panel_type")
    decision = evaluate(_panel_scope(example_scope), missing, workspace=tmp_path)
    assert not decision.allowed
    assert "panel type is missing" in decision.reasons

    mismatched = _panel_objective()
    mismatched["panel_type"] = "service_console"
    decision = evaluate(_panel_scope(example_scope), mismatched, workspace=tmp_path)
    assert not decision.allowed
    assert "panel type does not match scoped panel" in decision.reasons


@pytest.mark.parametrize(
    "unsafe_action",
    [
        "brute_force",
        "credential_guessing",
        "credential_stuffing",
        "default_password_check",
        "destructive_panel_action",
        "login_attempt",
        "lockout_triggering",
        "panel_crawl",
        "password_spraying",
        "session_hijacking",
        "token_replay",
        "unsafe_crawling",
    ],
)
def test_unsafe_panel_actions_are_denied(example_scope, tmp_path, unsafe_action):
    objective = _panel_objective()
    objective["action"] = unsafe_action
    decision = evaluate(_panel_scope(example_scope), objective, workspace=tmp_path)
    assert not decision.allowed
    assert any(reason.startswith("panel action is denied") for reason in decision.reasons)


def test_requested_unsafe_panel_actions_are_denied(example_scope, tmp_path):
    objective = _panel_objective()
    objective["requested_actions"] = ["plan_panel_target_metadata", "brute_force"]
    decision = evaluate(_panel_scope(example_scope), objective, workspace=tmp_path)
    assert not decision.allowed
    assert "panel action is denied by safety boundary: brute_force" in decision.reasons


def test_configured_panel_denial_wins(example_scope, tmp_path):
    scope = _panel_scope(example_scope)
    scope["service_control_panels"]["panels"][0]["denied_actions"].append(
        "custom_denied_action"
    )
    objective = _panel_objective()
    objective["action"] = "custom_denied_action"
    decision = evaluate(scope, objective, workspace=tmp_path)
    assert not decision.allowed
    assert (
        "panel action is explicitly denied by scope: custom_denied_action"
        in decision.reasons
    )


def test_category_module_mismatch_cannot_bypass_panel_denials(example_scope, tmp_path):
    objective = _panel_objective()
    objective["category"] = "wstg_webapp"
    objective["action"] = "login_attempt"
    decision = evaluate(_panel_scope(example_scope), objective, workspace=tmp_path)
    assert not decision.allowed
    assert "objective category must match module" in decision.reasons
    assert "panel action is denied by safety boundary: login_attempt" in decision.reasons


def test_control_panel_module_summary_declares_safe_defaults():
    modules = {module["module_id"]: module for module in module_summary()["modules"]}
    panel_module = modules["service_control_panel"]
    assert panel_module["default_execution_mode"] == "dry_run"
    assert panel_module["network_silent_default"] is True
    assert panel_module["required_scope_fields"] == ["target_alias", "panel_alias"]
    assert "credential_guessing" in panel_module["denied_actions"]
