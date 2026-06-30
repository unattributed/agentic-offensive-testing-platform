from pathlib import Path

import pytest

from aotp.campaign import load_campaign
from aotp.campaign_loop import run_campaign
from aotp.campaign_state import load_state
from aotp.config import load_yaml


def test_dry_run_creates_state_events_and_evidence(project_root, tmp_path, example_scope):
    scope_path = project_root / "config/scope.example.yaml"
    campaign = load_campaign(str(project_root / "campaigns/authorized-webapp-campaign.example.yaml")).data
    state, state_path = run_campaign(example_scope, scope_path, campaign, workspace=tmp_path)
    assert state.current_status == "completed"
    assert len([event for event in state.events if event["event_type"] == "objective_result"]) == 2
    assert len(state.evidence_directories) == 2
    assert state_path.is_file()
    assert all((tmp_path / Path(item) / "evidence.json").is_file() for item in state.evidence_directories)


def test_policy_denial_stops_campaign(project_root, tmp_path, example_scope):
    campaign = load_yaml(project_root / "campaigns/sbom-config-crypto-campaign.example.yaml").data
    state, _ = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    assert state.current_status == "stopped_by_policy"
    assert state.stopped_modules
    evidence = tmp_path / state.evidence_directories[-1] / "evidence.json"
    assert evidence.is_file()


def test_campaign_resumes_from_checkpoint_without_repeating_evidence(
    project_root, tmp_path, example_scope
):
    scope_path = project_root / "config/scope.example.yaml"
    campaign = load_campaign(
        str(project_root / "campaigns/authorized-webapp-campaign.example.yaml")
    ).data
    first, state_path = run_campaign(
        example_scope,
        scope_path,
        campaign,
        workspace=tmp_path,
        max_steps=1,
    )
    assert first.current_status == "running"
    assert first.completed_modules == ["wstg-security-headers"]
    assert first.pending_modules == ["wstg-authn-session"]
    first_evidence = tmp_path / first.evidence_directories[0] / "evidence.json"
    first_contents = first_evidence.read_text()

    resumed, _ = run_campaign(
        example_scope,
        scope_path,
        campaign,
        workspace=tmp_path,
        state=load_state(state_path),
        state_path=state_path,
    )
    assert resumed.current_status == "completed"
    assert resumed.completed_modules == ["wstg-security-headers", "wstg-authn-session"]
    assert len(resumed.evidence_directories) == 2
    assert first_evidence.read_text() == first_contents


def test_campaign_resume_rejects_changed_scope(project_root, tmp_path, example_scope):
    scope_path = tmp_path / "scope.yaml"
    scope_path.write_text((project_root / "config/scope.example.yaml").read_text())
    campaign = load_campaign(
        str(project_root / "campaigns/authorized-webapp-campaign.example.yaml")
    ).data
    state, state_path = run_campaign(
        example_scope,
        scope_path,
        campaign,
        workspace=tmp_path,
        max_steps=1,
    )
    scope_path.write_text(scope_path.read_text() + "\n# changed\n")
    with pytest.raises(ValueError, match="scope file hash"):
        run_campaign(
            example_scope,
            scope_path,
            campaign,
            workspace=tmp_path,
            state=load_state(state_path),
            state_path=state_path,
        )


def test_campaign_budget_denial_creates_evidence_before_execution(
    project_root, tmp_path, example_scope
):
    campaign = load_campaign(
        str(project_root / "campaigns/authorized-webapp-campaign.example.yaml")
    ).data
    campaign["objectives"][0]["parameters"]["request_budget"] = 2
    campaign["limits"]["max_requests"] = 1
    state, _ = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    assert state.current_status == "stopped_by_budget"
    assert state.stop_condition_history == ["request_limit"]
    assert state.stopped_modules == ["wstg-security-headers"]
    evidence = tmp_path / state.evidence_directories[0] / "evidence.json"
    assert '"tool": "safety-budget"' in evidence.read_text()
    assert '"request_count": 0' in evidence.read_text()
