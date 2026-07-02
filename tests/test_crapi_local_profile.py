import pytest

from aotp.lab_targets.crapi import (
    CRAPI_BASE_URL,
    CRAPI_MAILHOG_URL,
    CRAPI_PROJECT_NAME,
    CRAPI_WEB_PORT,
    CapiLocalProfile,
    CapiProfileError,
    build_local_crapi_wstg_profile,
    local_crapi_profile,
)
from aotp.wstg import WSTGAdapterFamily, WSTGPlanDisposition, WSTGSafetyTier, build_wstg_engine_plan


def test_local_crapi_profile_is_loopback_compose_managed_and_ephemeral() -> None:
    profile = local_crapi_profile()

    assert profile.target_alias == "local-crapi"
    assert profile.base_url == CRAPI_BASE_URL
    assert profile.mailhog_url == CRAPI_MAILHOG_URL
    assert profile.project_name == CRAPI_PROJECT_NAME
    assert profile.web_port == CRAPI_WEB_PORT
    assert profile.compose_required is True
    assert profile.live_runtime_status == "pending_unsupported"
    assert profile.network_exposure == "loopback-only"
    assert profile.reset_required_before_campaign is True
    assert profile.persistent_storage_allowed is False
    assert "127.0.0.1:8888" in profile.loopback_ports
    assert "127.0.0.1:8025" in profile.loopback_ports
    assert profile.compose_environment["LISTEN_IP"] == "127.0.0.1"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("base_url", "http://0.0.0.0:8888/"),
        ("base_url", "https://127.0.0.1:8888/"),
        ("mailhog_url", "http://127.0.0.1:8026/"),
        ("host", "0.0.0.0"),
        ("target_alias", "crapi"),
        ("project_name", "crapi"),
        ("network_exposure", "lan"),
        ("reset_required_before_campaign", False),
        ("persistent_storage_allowed", True),
        ("compose_required", False),
        ("live_runtime_status", "implemented"),
    ],
)
def test_local_crapi_profile_rejects_unsafe_configuration(field: str, value: object) -> None:
    with pytest.raises(CapiProfileError):
        CapiLocalProfile(**{field: value})


def test_local_crapi_wstg_profile_focuses_api_authz_and_business_logic() -> None:
    engine_profile = build_local_crapi_wstg_profile(max_ready_tests=18)
    plan = build_wstg_engine_plan(engine_profile)

    assert engine_profile.base_url == "http://127.0.0.1:8888/"
    assert engine_profile.target_alias == "local-crapi"
    assert WSTGSafetyTier.PASSIVE in engine_profile.allowed_safety_tiers
    assert WSTGSafetyTier.SAFE_ACTIVE in engine_profile.allowed_safety_tiers
    assert WSTGSafetyTier.INTRUSIVE_ACTIVE not in engine_profile.allowed_safety_tiers
    assert WSTGAdapterFamily.API in engine_profile.allowed_adapter_families
    assert WSTGAdapterFamily.MULTI_STEP in engine_profile.allowed_adapter_families
    assert engine_profile.allowed_categories is not None
    assert {"ATHZ", "BUSL", "APIT"}.issubset(engine_profile.allowed_categories)
    assert len(plan.ready_tests) == 18
    assert any(test.disposition is WSTGPlanDisposition.DEFERRED for test in plan.planned_tests)
    assert all("127.0.0.1:8888" in test.arguments["base_url"] for test in plan.planned_tests)
