from aotp.wstg.auth_boundary import evaluate_auth_boundary_check
from aotp.wstg.objective_generator import WSTGCampaignScope, generate_wstg_objectives
from aotp.wstg.strategy_map import ExecutableFamily, WSTGPhase, build_default_strategy_map


def _auth_objective():
    scope = WSTGCampaignScope(
        campaign_id="campaign-17",
        target_alias="owned-app",
        base_url="https://example.test",
        authorization_reference="authz-17",
        operator_approved=True,
        allowed_phases=frozenset({WSTGPhase.AUTH}),
        approved_families=frozenset({ExecutableFamily.AUTH_BOUNDARY}),
        authenticated=True,
    )
    return generate_wstg_objectives(scope, build_default_strategy_map())[0]


def test_auth_boundary_denies_without_approval_reference():
    decision = evaluate_auth_boundary_check(
        _auth_objective(),
        approved=False,
        approval_reference=None,
        authenticated_context=True,
    )

    assert not decision.allowed
    assert "authentication boundary approval is required" in decision.reasons


def test_auth_boundary_allows_approved_authenticated_context():
    decision = evaluate_auth_boundary_check(
        _auth_objective(),
        approved=True,
        approval_reference="approval-17-auth",
        authenticated_context=True,
    )

    assert decision.allowed
    assert decision.evidence_classification == "restricted"
