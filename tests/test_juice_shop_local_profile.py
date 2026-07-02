import pytest

from aotp.lab_targets.juice_shop import (
    JUICE_SHOP_BASE_URL,
    JUICE_SHOP_CONTAINER_NAME,
    JUICE_SHOP_IMAGE,
    JUICE_SHOP_PORT,
    JuiceShopLocalProfile,
    JuiceShopProfileError,
    build_local_juice_shop_wstg_profile,
    local_juice_shop_profile,
)
from aotp.wstg import WSTGAdapterFamily, WSTGPlanDisposition, WSTGSafetyTier, build_wstg_engine_plan


def test_local_juice_shop_profile_is_loopback_only_and_ephemeral() -> None:
    profile = local_juice_shop_profile()

    assert profile.base_url == JUICE_SHOP_BASE_URL
    assert profile.image == JUICE_SHOP_IMAGE
    assert profile.container_name == JUICE_SHOP_CONTAINER_NAME
    assert profile.port == JUICE_SHOP_PORT
    assert profile.docker_port_binding == "127.0.0.1:3000:3000"
    assert profile.network_exposure == "loopback-only"
    assert profile.reset_required_before_campaign is True
    assert profile.persistent_storage_allowed is False
    assert profile.docker_labels()["aotp.reset_required"] == "true"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("base_url", "http://0.0.0.0:3000/"),
        ("base_url", "https://127.0.0.1:3000/"),
        ("host", "0.0.0.0"),
        ("network_exposure", "lan"),
        ("reset_required_before_campaign", False),
        ("persistent_storage_allowed", True),
        ("image", "somebody/juice-shop"),
    ],
)
def test_local_juice_shop_profile_rejects_unsafe_configuration(field: str, value: object) -> None:
    kwargs = {field: value}
    with pytest.raises(JuiceShopProfileError):
        JuiceShopLocalProfile(**kwargs)


def test_local_juice_shop_wstg_profile_plans_safe_benchmark_campaign() -> None:
    profile = build_local_juice_shop_wstg_profile(max_ready_tests=12)
    plan = build_wstg_engine_plan(profile)

    assert profile.base_url == "http://127.0.0.1:3000/"
    assert WSTGSafetyTier.PASSIVE in profile.allowed_safety_tiers
    assert WSTGSafetyTier.SAFE_ACTIVE in profile.allowed_safety_tiers
    assert WSTGSafetyTier.INTRUSIVE_ACTIVE not in profile.allowed_safety_tiers
    assert WSTGAdapterFamily.HTTP in profile.allowed_adapter_families
    assert WSTGAdapterFamily.API in profile.allowed_adapter_families
    assert len(plan.ready_tests) == 12
    assert any(test.disposition is WSTGPlanDisposition.DEFERRED for test in plan.planned_tests)
    assert all("127.0.0.1:3000" in test.arguments["base_url"] for test in plan.planned_tests)
