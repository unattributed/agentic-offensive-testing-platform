import json
import stat

import pytest

from aotp.campaign_state import CampaignState, load_state, save_state, validate_state


def make_state():
    return CampaignState(
        campaign_id="id",
        campaign_name="name",
        campaign_definition_hash="a" * 64,
        scope_file_hash="b" * 64,
        rules_of_engagement_reference="roe",
        authorization_reference="authorization",
        operator_alias="operator",
        start_time="2026-01-01T00:00:00+00:00",
        last_updated_time="2026-01-01T00:00:00+00:00",
        current_status="running",
        pending_modules=["objective-one"],
    )


def test_campaign_state_round_trip(tmp_path):
    state = make_state()
    path = save_state(state, tmp_path / "state.json")
    assert load_state(path).campaign_id == "id"
    assert load_state(path).state_revision == 1
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_campaign_state_detects_tampering(tmp_path):
    path = save_state(make_state(), tmp_path / "state.json")
    envelope = json.loads(path.read_text())
    envelope["state"]["current_status"] = "completed"
    path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity check failed"):
        load_state(path)


def test_campaign_state_rejects_overlapping_dispositions():
    state = make_state()
    state.completed_modules = ["objective-one"]
    with pytest.raises(ValueError, match="disposition overlap"):
        validate_state(state)


def test_campaign_state_rejects_invalid_completion():
    state = make_state()
    state.current_status = "completed"
    with pytest.raises(ValueError, match="cannot retain pending"):
        validate_state(state)
