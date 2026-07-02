from __future__ import annotations

from pathlib import Path

import pytest

from aotp.campaigns.target_runtime import (
    CampaignTargetRuntime,
    TargetRuntimeError,
    build_juice_shop_target_runtime,
    runtime_from_local_target_registry,
)


def test_juice_shop_runtime_uses_generic_contract() -> None:
    runtime = build_juice_shop_target_runtime(max_actions=5, max_ready_tests=12)

    assert runtime.target_alias == "local-juice-shop"
    assert runtime.normalized_base_url == "http://127.0.0.1:3000/"
    assert runtime.network_exposure == "loopback-only"
    assert runtime.implemented_live_target is True
    assert runtime.reset_required_before_campaign is True
    assert "/" in runtime.safe_paths
    assert runtime.build_wstg_profile(campaign_id="local-juice-shop-generic", max_ready_tests=12).target_alias == "local-juice-shop"


def test_target_runtime_rejects_non_loopback_when_loopback_only() -> None:
    with pytest.raises(TargetRuntimeError):
        CampaignTargetRuntime(
            target_alias="local-bad",
            base_url="http://example.com/",
            authorization_reference="local-test",
            network_exposure="loopback-only",
            implemented_live_target=True,
            reset_required_before_campaign=True,
            safe_paths=("/",),
        )


def test_planned_crapi_registry_entry_is_not_live_executable() -> None:
    with pytest.raises(TargetRuntimeError, match="not live-executable"):
        runtime_from_local_target_registry("local-crapi")
