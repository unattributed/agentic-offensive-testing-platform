from pathlib import Path


def test_agentic_campaign_runner_uses_venv_and_resets_before_campaign() -> None:
    script = Path("scripts/run-local-juice-shop-agentic-campaign.sh").read_text(encoding="utf-8")

    assert 'PYTHON="$REPO/.venv/bin/python"' in script
    assert 'test -x "$PYTHON"' in script
    assert "juice-shop-local-reset.sh" in script
    assert "--no-reset" in script
    assert "python -m aotp.campaigns.juice_shop_campaign" not in script
    assert '"$PYTHON" -m aotp.campaigns.juice_shop_campaign' in script
    assert "127.0.0.1:$PORT" in script


def test_agentic_campaign_validation_runner_has_optional_live_campaign() -> None:
    script = Path("scripts/run-sprint18-followup-local-juice-shop-agentic-campaign-validation.sh").read_text(encoding="utf-8")

    assert "--live-campaign" in script
    assert "run-local-juice-shop-agentic-campaign.sh" in script
    assert 'PYTHON="$REPO/.venv/bin/python"' in script
    assert "tests/test_juice_shop_agentic_campaign.py" in script
    assert "tests/test_juice_shop_agentic_campaign_scripts.py" in script
