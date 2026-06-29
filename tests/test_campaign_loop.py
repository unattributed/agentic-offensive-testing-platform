from pathlib import Path

from aotp.campaign import load_campaign
from aotp.campaign_loop import run_campaign
from aotp.config import load_yaml


def test_dry_run_creates_state_events_and_evidence(project_root, tmp_path, example_scope):
    scope_path = project_root / "config/scope.example.yaml"
    campaign = load_campaign(str(project_root / "campaigns/authorized-webapp-campaign.example.yaml")).data
    state, state_path = run_campaign(example_scope, scope_path, campaign, workspace=tmp_path)
    assert state.current_status == "completed"
    assert len(state.events) == 2
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
