import pytest

from aotp.roe import RulesOfEngagement
from aotp.tool_risk_tiers import ToolRiskTier
from aotp.wstg.objective_generator import WSTGCampaignScope, WSTGObjectiveError, generate_wstg_objectives
from aotp.wstg.strategy_map import ExecutableFamily, WSTGPhase, build_default_strategy_map


def _scope(**overrides):
    values = {
        "campaign_id": "campaign-17",
        "target_alias": "owned-app",
        "base_url": "https://example.test",
        "authorization_reference": "authz-17",
        "operator_approved": True,
        "allowed_phases": frozenset({WSTGPhase.PASSIVE, WSTGPhase.BROWSER}),
        "approved_families": frozenset({
            ExecutableFamily.HTTP_METADATA,
            ExecutableFamily.WELL_KNOWN_TEXT,
            ExecutableFamily.TLS_METADATA,
            ExecutableFamily.PLAYWRIGHT_PASSIVE_METADATA,
        }),
    }
    values.update(overrides)
    return WSTGCampaignScope(**values)


def test_generate_objectives_stays_in_scope_and_roe():
    roe = RulesOfEngagement(
        campaign_id="campaign-17",
        target_alias="owned-app",
        authorization_reference="authz-17",
        operator_approved=True,
        allowed_tool_names=frozenset({"http_metadata", "well_known_text", "tls_metadata", "playwright_passive_metadata", }),
        allowed_risk_tiers=frozenset({ToolRiskTier.PASSIVE_METADATA, ToolRiskTier.PASSIVE_BROWSER}),
        allowed_hosts=frozenset({"example.test"}),
        allowed_ports=frozenset({443}),
        allowed_schemes=frozenset({"https"}),
        evidence_classifications=frozenset({"public", "restricted"}),
    )

    objectives = generate_wstg_objectives(_scope(), build_default_strategy_map(), roe=roe)

    assert {objective.phase for objective in objectives} <= {WSTGPhase.PASSIVE, WSTGPhase.BROWSER}
    assert all("example.test" in repr(objective.arguments) for objective in objectives)
    assert {objective.wstg_id for objective in objectives} >= {"WSTG-v42-INFO-02", "WSTG-v42-INFO-03"}


def test_auth_and_session_objectives_require_explicit_scope_flags():
    objectives = generate_wstg_objectives(
        _scope(
            allowed_phases=frozenset({WSTGPhase.AUTH}),
            approved_families=frozenset({ExecutableFamily.AUTH_BOUNDARY, ExecutableFamily.SESSION_MANAGEMENT}),
        ),
        build_default_strategy_map(),
    )
    assert objectives == ()

    approved = generate_wstg_objectives(
        _scope(
            allowed_phases=frozenset({WSTGPhase.AUTH}),
            approved_families=frozenset({ExecutableFamily.AUTH_BOUNDARY, ExecutableFamily.SESSION_MANAGEMENT}),
            authenticated=True,
            allow_session_material=True,
        ),
        build_default_strategy_map(),
    )
    assert {objective.family for objective in approved} == {ExecutableFamily.AUTH_BOUNDARY, ExecutableFamily.SESSION_MANAGEMENT}


def test_scope_denies_url_credentials_and_missing_approval():
    with pytest.raises(WSTGObjectiveError):
        _scope(base_url="https://user:pass@example.test")
    with pytest.raises(WSTGObjectiveError):
        _scope(operator_approved=False)


def test_roe_filters_unallowed_tools_risk_and_classification():
    roe = RulesOfEngagement(
        campaign_id="campaign-17",
        target_alias="owned-app",
        authorization_reference="authz-17",
        operator_approved=True,
        allowed_tool_names=frozenset({"http_metadata"}),
        allowed_risk_tiers=frozenset({ToolRiskTier.PASSIVE_METADATA}),
        allowed_hosts=frozenset({"example.test"}),
        allowed_ports=frozenset({443}),
        allowed_schemes=frozenset({"https"}),
        evidence_classifications=frozenset({"public"}),
    )

    objectives = generate_wstg_objectives(
        _scope(
            allowed_phases=frozenset({WSTGPhase.PASSIVE, WSTGPhase.BROWSER, WSTGPhase.VALIDATION}),
            approved_families=frozenset({
                ExecutableFamily.HTTP_METADATA,
                ExecutableFamily.WELL_KNOWN_TEXT,
                ExecutableFamily.PLAYWRIGHT_PASSIVE_METADATA,
                ExecutableFamily.ZAP_PASSIVE_BASELINE,
            }),
            allow_active_validation=True,
        ),
        build_default_strategy_map(),
        roe=roe,
    )

    assert [objective.tool_name for objective in objectives] == ["http_metadata"]
