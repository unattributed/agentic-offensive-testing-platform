import pytest

from aotp.wstg.catalog import EXPECTED_WSTG_V42_TEST_COUNT, WSTGAdapterFamily, WSTGSafetyTier
from aotp.wstg.engine import WSTGEngineError, WSTGEngineProfile, WSTGPlanDisposition, build_wstg_engine_plan


def _profile(**overrides):
    values = {
        "campaign_id": "campaign-18",
        "target_alias": "authorized-app",
        "base_url": "https://example.test",
        "authorization_reference": "authz-18",
        "operator_approved": True,
        "allowed_safety_tiers": frozenset({WSTGSafetyTier.PASSIVE, WSTGSafetyTier.SAFE_ACTIVE}),
        "allowed_adapter_families": frozenset({
            WSTGAdapterFamily.HTTP,
            WSTGAdapterFamily.BROWSER,
            WSTGAdapterFamily.TLS,
            WSTGAdapterFamily.API,
            WSTGAdapterFamily.MULTI_STEP,
            WSTGAdapterFamily.MANUAL,
        }),
        "authenticated": True,
        "multi_role": True,
        "max_ready_tests": 25,
    }
    values.update(overrides)
    return WSTGEngineProfile(**values)


def test_engine_plan_contains_complete_wstg_matrix_not_only_ready_tests():
    plan = build_wstg_engine_plan(_profile())

    assert len(plan.planned_tests) == EXPECTED_WSTG_V42_TEST_COUNT
    assert len(plan.ready_tests) == 25
    assert plan.coverage_summary()["total"] == EXPECTED_WSTG_V42_TEST_COUNT
    assert {test.wstg_id for test in plan.planned_tests} >= {
        "WSTG-v42-INFO-01",
        "WSTG-v42-ATHZ-04",
        "WSTG-v42-INPV-19",
        "WSTG-v42-CLNT-13",
        "WSTG-v42-APIT-01",
    }


def test_engine_defers_unauthorized_intrusive_and_auth_required_tests():
    plan = build_wstg_engine_plan(
        _profile(
            allowed_safety_tiers=frozenset({WSTGSafetyTier.PASSIVE}),
            authenticated=False,
            multi_role=False,
            max_ready_tests=None,
        )
    )

    sql_injection = next(test for test in plan.planned_tests if test.wstg_id == "WSTG-v42-INPV-05")
    authz_bypass = next(test for test in plan.planned_tests if test.wstg_id == "WSTG-v42-ATHZ-02")

    assert sql_injection.disposition is WSTGPlanDisposition.DEFERRED
    assert "safety tier not approved" in " ".join(sql_injection.reasons)
    assert "intrusive active testing requires explicit campaign approval" in " ".join(sql_injection.reasons)
    assert authz_bypass.disposition is WSTGPlanDisposition.DEFERRED
    assert "multi-role authorization context required" in " ".join(authz_bypass.reasons)


def test_engine_profile_requires_approval_and_clean_target_url():
    with pytest.raises(WSTGEngineError):
        _profile(operator_approved=False)
    with pytest.raises(WSTGEngineError):
        _profile(base_url="https://user:password@example.test")
