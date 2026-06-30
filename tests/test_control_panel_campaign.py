from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aotp.campaign import parse_campaign
from aotp.campaign_control import apply_review_decision
from aotp.campaign_loop import run_campaign
from aotp.campaign_state import load_state
from aotp.config import ConfigError, load_yaml
from aotp.evidence import load_manifest, sha256_file, verify_evidence_directory


def _scope(project_root: Path) -> dict:
    return load_yaml(project_root / "config/scope.panel-dry-run.example.yaml").data


def _campaign(project_root: Path) -> dict:
    return load_yaml(
        project_root / "campaigns/service-control-panel-campaign.example.yaml"
    ).data


def test_panel_campaign_schema_requires_panel_fields_and_lockout_stop(project_root):
    campaign = _campaign(project_root)
    assert parse_campaign(campaign).objectives[0].module == "service_control_panel"

    missing_alias = deepcopy(campaign)
    missing_alias["objectives"][0].pop("panel_alias")
    with pytest.raises(ConfigError, match="panel_alias"):
        parse_campaign(missing_alias)

    missing_stop = deepcopy(campaign)
    missing_stop["stop_conditions"].remove("authentication_lockout_risk")
    with pytest.raises(ConfigError, match="authentication_lockout_risk"):
        parse_campaign(missing_stop)


def test_panel_campaign_writes_integrity_verified_panel_evidence(project_root, tmp_path):
    state, _ = run_campaign(
        _scope(project_root),
        project_root / "config/scope.panel-dry-run.example.yaml",
        _campaign(project_root),
        workspace=tmp_path,
    )
    assert state.current_status == "completed"
    assert len(state.evidence_directories) == 1
    evidence_dir = tmp_path / state.evidence_directories[0]
    manifest = load_manifest(evidence_dir / "evidence.json")
    assert manifest.module_name == "service_control_panel"
    assert manifest.request_count == 0
    assert (evidence_dir / "panel-evidence.json").is_file()
    assert verify_evidence_directory(evidence_dir) == []


def test_lockout_risk_pauses_before_execution_and_requires_bound_review(
    project_root,
    tmp_path,
):
    campaign = _campaign(project_root)
    campaign["campaign_id"] = "example-panel-lockout-pause"
    campaign["objectives"][0]["lockout_risk_detected"] = True
    scope_path = project_root / "config/scope.panel-dry-run.example.yaml"
    state, state_path = run_campaign(
        _scope(project_root),
        scope_path,
        campaign,
        workspace=tmp_path,
    )

    assert state.current_status == "paused_for_human_review"
    assert state.pending_review["stop_condition"] == "authentication_lockout_risk"
    assert state.current_objective_id == "panel-safe-observations"
    pause_dir = tmp_path / state.evidence_directories[0]
    pause_manifest = load_manifest(pause_dir / "evidence.json")
    assert pause_manifest.tool == "panel-lockout-risk-gate"
    assert pause_manifest.request_count == 0
    pause_event = [
        event for event in state.events if event["event_type"] == "campaign_paused"
    ][-1]
    assert pause_event["details"]["stop_condition"] == "authentication_lockout_risk"

    review = {
        "schema_version": "1.0",
        "decision_id": "panel-lockout-review",
        "campaign_id": state.campaign_id,
        "objective_id": state.current_objective_id,
        "operator_alias": state.operator_alias,
        "decision": "approved",
        "decided_at_utc": "2026-06-30T00:00:00Z",
        "state_sha256": sha256_file(state_path),
        "reason": "Human reviewer confirmed the dry-run objective remains safe.",
    }
    apply_review_decision(
        state,
        state_path,
        review,
        now=datetime(2026, 6, 30, 1, tzinfo=UTC),
    )
    resumed, _ = run_campaign(
        _scope(project_root),
        scope_path,
        campaign,
        workspace=tmp_path,
        state=load_state(state_path),
        state_path=state_path,
    )
    assert resumed.current_status == "completed"
    assert resumed.reviewed_objectives == ["panel-safe-observations"]
    executed_dir = tmp_path / resumed.evidence_directories[-1]
    assert (executed_dir / "panel-evidence.json").is_file()
