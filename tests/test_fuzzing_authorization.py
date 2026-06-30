from __future__ import annotations

from copy import deepcopy

import pytest

from aotp.bounded_fuzzing import FUZZING_UNSAFE_ACTIONS
from aotp.config import ConfigError, load_yaml, parse_scope
from aotp.policy_gate import evaluate


def _objective(project_root) -> dict:
    objective = load_yaml(project_root / "cases/bounded-fuzzing.example.yaml").data
    objective["human_approved"] = True
    return objective


def _authorized_scope(example_scope: dict) -> dict:
    scope = deepcopy(example_scope)
    scope["fuzzing"].update(
        {
            "authorized": True,
            "approved_actions": ["plan_bounded_fuzzing"],
            "denied_actions": sorted(FUZZING_UNSAFE_ACTIONS),
        }
    )
    return scope


def test_default_scope_denies_fuzzing(project_root, example_scope, tmp_path):
    decision = evaluate(
        example_scope,
        _objective(project_root),
        workspace=tmp_path,
    )
    assert not decision.allowed
    assert "fuzzing is not explicitly authorized" in decision.reasons
    assert "fuzzing action is not explicitly approved: plan_bounded_fuzzing" in decision.reasons


def test_authorized_scope_requires_exact_action_approval(
    project_root,
    example_scope,
    tmp_path,
):
    objective = _objective(project_root)
    objective["action"] = "enumerate_fuzz_targets"
    decision = evaluate(
        _authorized_scope(example_scope),
        objective,
        workspace=tmp_path,
    )
    assert not decision.allowed
    assert (
        "fuzzing action is not explicitly approved: enumerate_fuzz_targets"
        in decision.reasons
    )


def test_authorized_approved_fuzzing_dry_run_passes_policy(
    project_root,
    example_scope,
    tmp_path,
):
    decision = evaluate(
        _authorized_scope(example_scope),
        _objective(project_root),
        workspace=tmp_path,
    )
    assert decision.allowed, decision.reasons


def test_configured_fuzzing_denial_wins(
    project_root,
    example_scope,
    tmp_path,
):
    objective = _objective(project_root)
    objective["action"] = "destructive_fuzzing"
    decision = evaluate(
        _authorized_scope(example_scope),
        objective,
        workspace=tmp_path,
    )
    assert not decision.allowed
    assert (
        "fuzzing action is explicitly denied by scope: destructive_fuzzing"
        in decision.reasons
    )


def test_state_changing_fuzzing_remains_separately_gated(
    project_root,
    example_scope,
    tmp_path,
):
    objective = _objective(project_root)
    objective["state_changing"] = True
    decision = evaluate(
        _authorized_scope(example_scope),
        objective,
        workspace=tmp_path,
    )
    assert not decision.allowed
    assert "state-changing fuzzing is not explicitly authorized" in decision.reasons


def test_fuzzing_scope_rejects_contradictory_actions(example_scope):
    scope = _authorized_scope(example_scope)
    scope["fuzzing"]["denied_actions"].append("plan_bounded_fuzzing")
    with pytest.raises(ConfigError, match="overlap"):
        parse_scope(scope)


def test_fuzzing_scope_rejects_approval_when_disabled(example_scope):
    example_scope["fuzzing"]["approved_actions"] = ["plan_bounded_fuzzing"]
    with pytest.raises(ConfigError, match="must be empty"):
        parse_scope(example_scope)
