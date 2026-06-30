from datetime import UTC, datetime

import pytest

from aotp.campaign import load_campaign
from aotp.campaign_control import apply_review_decision, request_operator_stop
from aotp.campaign_loop import run_campaign
from aotp.campaign_state import load_state
from aotp.evidence import sha256_file


def _review(state, state_path, decision="approved"):
    return {
        "schema_version": "1.0",
        "decision_id": f"review-{decision}",
        "campaign_id": state.campaign_id,
        "objective_id": state.current_objective_id,
        "operator_alias": state.operator_alias,
        "decision": decision,
        "decided_at_utc": "2026-06-30T00:00:00Z",
        "state_sha256": sha256_file(state_path),
        "reason": "synthetic test decision",
    }


def test_pre_execution_review_approval_resumes_and_completes(
    project_root, tmp_path, example_scope
):
    campaign = load_campaign(
        str(project_root / "campaigns/bug-bounty-efficiency-campaign.example.yaml")
    ).data
    state, state_path = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    assert state.current_status == "paused_for_human_review"
    assert state.pending_review["phase"] == "pre_execution"
    assert state.current_objective_id == "report-quality-review"

    apply_review_decision(
        state,
        state_path,
        _review(state, state_path),
        now=datetime(2026, 6, 30, 1, tzinfo=UTC),
    )
    resumed, _ = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
        state=load_state(state_path),
        state_path=state_path,
    )
    assert resumed.current_status == "completed"
    assert resumed.reviewed_objectives == ["report-quality-review"]
    assert resumed.completed_modules == [
        "prior-testing-memory-review",
        "report-quality-review",
    ]


def test_review_decision_must_bind_exact_checkpoint(project_root, tmp_path, example_scope):
    campaign = load_campaign(
        str(project_root / "campaigns/bug-bounty-efficiency-campaign.example.yaml")
    ).data
    state, state_path = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    review = _review(state, state_path)
    review["state_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="does not match checkpoint"):
        apply_review_decision(state, state_path, review)


def test_review_denial_stops_campaign(project_root, tmp_path, example_scope):
    campaign = load_campaign(
        str(project_root / "campaigns/bug-bounty-efficiency-campaign.example.yaml")
    ).data
    state, state_path = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    apply_review_decision(
        state,
        state_path,
        _review(state, state_path, "denied"),
        now=datetime(2026, 6, 30, 1, tzinfo=UTC),
    )
    assert load_state(state_path).current_status == "stopped_by_condition"


def test_operator_stop_persists_terminal_state(project_root, tmp_path, example_scope):
    campaign = load_campaign(
        str(project_root / "campaigns/authorized-webapp-campaign.example.yaml")
    ).data
    state, state_path = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
        max_steps=1,
    )
    request_operator_stop(state, state_path)
    stopped = load_state(state_path)
    assert stopped.current_status == "stopped_by_operator"
    assert stopped.operator_stop_requested
    assert "operator_stop" in stopped.stop_condition_history
