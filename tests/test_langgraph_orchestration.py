import stat
from datetime import UTC, datetime

import pytest

from aotp.campaign import load_campaign
from aotp.campaign_events import verify_state_event_log
from aotp.campaign_loop import run_campaign
from aotp.campaign_state import load_state
from aotp.evidence import sha256_file
from aotp.langgraph_orchestration import LangGraphCampaignOrchestrator


def _orchestrator(project_root, workspace, example_scope, campaign_name):
    scope_path = project_root / "config/scope.example.yaml"
    campaign = load_campaign(str(project_root / "campaigns" / campaign_name)).data
    return LangGraphCampaignOrchestrator(
        scope=example_scope,
        scope_path=scope_path,
        campaign=campaign,
        workspace=workspace,
    )


def test_langgraph_completion_matches_deterministic_engine(
    project_root, tmp_path, example_scope
):
    campaign_name = "authorized-webapp-campaign.example.yaml"
    campaign = load_campaign(str(project_root / "campaigns" / campaign_name)).data
    deterministic, _ = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path / "deterministic",
    )
    with _orchestrator(project_root, tmp_path / "graph", example_scope, campaign_name) as graph:
        snapshot = graph.start()
        graph_state = load_state(graph.state_path)
        assert snapshot["status"] == deterministic.current_status == "completed"
        assert graph_state.completed_modules == deterministic.completed_modules
        assert graph_state.stopped_modules == deterministic.stopped_modules
        assert verify_state_event_log(graph_state, graph.state_path) == []
        assert stat.S_IMODE(graph.checkpoint_db.stat().st_mode) == 0o600
        assert stat.S_IMODE(graph.checkpoint_db.parent.stat().st_mode) == 0o700
        for sqlite_sidecar in graph.checkpoint_db.parent.glob(
            graph.checkpoint_db.name + "-*"
        ):
            assert stat.S_IMODE(sqlite_sidecar.stat().st_mode) == 0o600


def test_langgraph_policy_stop_matches_deterministic_engine(
    project_root, tmp_path, example_scope
):
    campaign_name = "sbom-config-crypto-campaign.example.yaml"
    campaign = load_campaign(str(project_root / "campaigns" / campaign_name)).data
    deterministic, _ = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path / "deterministic",
    )
    with _orchestrator(project_root, tmp_path / "graph", example_scope, campaign_name) as graph:
        snapshot = graph.start()
        graph_state = load_state(graph.state_path)
        assert snapshot["status"] == deterministic.current_status == "stopped_by_policy"
        assert graph_state.completed_modules == deterministic.completed_modules
        assert graph_state.stopped_modules == deterministic.stopped_modules


def test_langgraph_sqlite_checkpoint_survives_restart_and_review(
    project_root, tmp_path, example_scope
):
    campaign_name = "bug-bounty-efficiency-campaign.example.yaml"
    graph = _orchestrator(project_root, tmp_path, example_scope, campaign_name)
    snapshot = graph.start()
    assert snapshot["status"] == "paused_for_human_review"
    state = load_state(graph.state_path)
    state_path = graph.state_path
    checkpoint_db = graph.checkpoint_db
    thread_id = graph.thread_id
    graph.close()

    review = {
        "schema_version": "1.0",
        "decision_id": "langgraph-review-approved",
        "campaign_id": state.campaign_id,
        "objective_id": state.current_objective_id,
        "operator_alias": state.operator_alias,
        "decision": "approved",
        "decided_at_utc": datetime.now(UTC).isoformat(),
        "state_sha256": sha256_file(state_path),
        "reason": "synthetic durable checkpoint test",
    }
    resumed = _orchestrator(project_root, tmp_path, example_scope, campaign_name)
    assert resumed.checkpoint_db == checkpoint_db
    assert resumed.thread_id == thread_id
    snapshot = resumed.resume(review)
    assert snapshot["status"] == "completed"
    final_state = load_state(resumed.state_path)
    assert final_state.completed_modules == [
        "prior-testing-memory-review",
        "report-quality-review",
    ]
    assert verify_state_event_log(final_state, resumed.state_path) == []
    resumed.close()


def test_langgraph_checkpoint_does_not_store_scope_document(
    project_root, tmp_path, example_scope
):
    graph = _orchestrator(
        project_root,
        tmp_path,
        example_scope,
        "authorized-webapp-campaign.example.yaml",
    )
    graph.start()
    graph.close()
    database = (tmp_path / ".aotp/checkpoints/example-webapp-dry-run.sqlite").read_bytes()
    assert b"example-only" not in database


def test_langgraph_checkpoint_cannot_escape_workspace(
    project_root, tmp_path, example_scope
):
    campaign = load_campaign(
        str(project_root / "campaigns/authorized-webapp-campaign.example.yaml")
    ).data
    with pytest.raises(ValueError, match="must stay within workspace"):
        LangGraphCampaignOrchestrator(
            scope=example_scope,
            scope_path=project_root / "config/scope.example.yaml",
            campaign=campaign,
            workspace=tmp_path / "workspace",
            checkpoint_db=tmp_path / "outside.sqlite",
        )
