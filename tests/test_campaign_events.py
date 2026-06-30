import json

from aotp.campaign import load_campaign
from aotp.campaign_events import resolve_event_log, verify_event_log, verify_state_event_log
from aotp.campaign_loop import run_campaign


def test_campaign_event_log_is_contiguous_and_hash_chained(
    project_root, tmp_path, example_scope
):
    campaign = load_campaign(
        str(project_root / "campaigns/authorized-webapp-campaign.example.yaml")
    ).data
    state, state_path = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    event_path = resolve_event_log(state, state_path)
    assert verify_event_log(event_path) == []
    assert verify_state_event_log(state, state_path) == []
    events = [json.loads(line) for line in event_path.read_text().splitlines()]
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert events[0]["event_type"] == "campaign_started"
    assert events[-1]["event_type"] == "campaign_completed"
    assert all(
        events[index]["previous_event_hash"] == events[index - 1]["event_hash"]
        for index in range(1, len(events))
    )


def test_campaign_event_log_detects_modification(project_root, tmp_path, example_scope):
    campaign = load_campaign(
        str(project_root / "campaigns/authorized-webapp-campaign.example.yaml")
    ).data
    state, state_path = run_campaign(
        example_scope,
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    event_path = resolve_event_log(state, state_path)
    lines = event_path.read_text().splitlines()
    event = json.loads(lines[1])
    event["outcome"] = "modified"
    lines[1] = json.dumps(event)
    event_path.write_text("\n".join(lines) + "\n")
    assert any("event hash does not match" in failure for failure in verify_event_log(event_path))
