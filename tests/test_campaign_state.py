from aotp.campaign_state import CampaignState, load_state, save_state


def test_campaign_state_round_trip(tmp_path):
    state = CampaignState(
        "id",
        "name",
        "hash",
        "roe",
        "authorization",
        "start",
        "updated",
        "running",
    )
    path = save_state(state, tmp_path / "state.json")
    assert load_state(path).campaign_id == "id"
