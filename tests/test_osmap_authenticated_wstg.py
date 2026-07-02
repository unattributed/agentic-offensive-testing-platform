from datetime import datetime, timedelta, timezone

import pytest

from aotp.agent_tools.osmap_authenticated_wstg import (
    AuthenticatedOSMAPRunnerError,
    AuthenticatedOSMAPWSTGRunner,
    SyntheticAuthenticatedObservation,
    review_authenticated_candidate,
)
from aotp.auth_session import AllowedRoute, AuthState, AuthenticatedSessionBoundary, LogoutCheckStatus
from aotp.integrations.osmap_route_map import build_osmap_route_auth_map
from aotp.integrations.osmap_source_review import review_osmap_source
from aotp.integrations.osmap_wstg_mapper import map_osmap_routes_to_wstg_requests
from aotp.wstg.execution_adapter import WSTGExecutionStatus
from aotp.wstg.objective_generator import WSTGCampaignScope
from aotp.wstg.strategy_map import ExecutableFamily, WSTGPhase


DIGEST = "c" * 64
SOURCE = '''
@app.route("/account/settings", methods=["GET"])
def settings():
    require_auth()
    session.get("user")
    return "settings"

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return "logout"
'''


def _future():
    return (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()


def _boundary():
    return AuthenticatedSessionBoundary(
        campaign_id="campaign-18",
        operator_alias="operator-one",
        target_alias="owned-app",
        account_alias="account-one",
        authorization_reference="authz-18",
        approval_reference="approval-18",
        rules_of_engagement_reference="roe-18",
        scope_sha256=DIGEST,
        approval_scope_sha256=DIGEST,
        approval_operator_alias="operator-one",
        approval_expires_utc=_future(),
        approved_permissions=frozenset({"authenticated_testing"}),
        allowed_routes=(
            AllowedRoute("/account/*", frozenset({"GET"})),
            AllowedRoute("/logout", frozenset({"POST"})),
        ),
        allowed_auth_states=frozenset({AuthState.AUTHENTICATED, AuthState.POST_LOGOUT}),
    )


def _request(tmp_path):
    root = tmp_path / "osmap"
    root.mkdir()
    (root / "app.py").write_text(SOURCE, encoding="utf-8")
    route_map = build_osmap_route_auth_map(review_osmap_source(root, workspace=tmp_path))
    scope = WSTGCampaignScope(
        campaign_id="campaign-18",
        target_alias="owned-app",
        base_url="https://example.test",
        authorization_reference="authz-18",
        operator_approved=True,
        allowed_phases=frozenset({WSTGPhase.AUTH}),
        approved_families=frozenset({ExecutableFamily.SESSION_MANAGEMENT, ExecutableFamily.AUTH_BOUNDARY}),
        authenticated=True,
        allow_session_material=True,
    )
    for candidate in map_osmap_routes_to_wstg_requests(route_map, scope, approval_reference="approval-18"):
        if candidate.request.arguments["path_pattern"] == "/account/settings":
            return candidate.request
    raise AssertionError("request not found")


def test_authenticated_runner_executes_synthetic_pass_with_redacted_evidence(tmp_path):
    result = AuthenticatedOSMAPWSTGRunner().execute(
        _request(tmp_path),
        boundary=_boundary(),
        observation=SyntheticAuthenticatedObservation(
            status="pass",
            summary="authenticated route returned expected redacted metadata",
            evidence_reference="authenticated-osmap/settings-redacted.json",
            evidence_payload={"route": "/account/settings", "cookie_present": True, "raw_value": "redacted"},
        ),
    )

    assert result.status is WSTGExecutionStatus.PASS
    assert result.evidence_references == ("authenticated-osmap/settings-redacted.json",)


def test_authenticated_runner_denies_out_of_route_execution(tmp_path):
    request = _request(tmp_path)
    request.arguments["path_pattern"] = "/admin"

    with pytest.raises(Exception):
        AuthenticatedOSMAPWSTGRunner().execute(request, boundary=_boundary())


def test_authenticated_runner_rejects_secret_material_in_metadata(tmp_path):
    with pytest.raises(AuthenticatedOSMAPRunnerError):
        SyntheticAuthenticatedObservation(
            status="pass",
            summary="bad",
            evidence_reference="authenticated-osmap/bad.json",
            evidence_payload={"Cookie": "session" + "id=raw-secret"},
        )


def test_authenticated_fail_creates_human_review_candidate_only(tmp_path):
    result = AuthenticatedOSMAPWSTGRunner().execute(
        _request(tmp_path),
        boundary=_boundary(),
        observation=SyntheticAuthenticatedObservation(
            status="fail",
            summary="post-login expectation failed with redacted evidence",
            evidence_reference="authenticated-osmap/settings-fail-redacted.json",
            evidence_payload={"route": "/account/settings", "decision": "fail"},
        ),
    )

    review = review_authenticated_candidate(result)
    assert result.finding_candidate is not None
    assert review["state"] == "candidate_needs_human_validation"
    assert review["may_report"] is False


def test_logout_boundary_summary_excludes_session_material():
    payload = AuthenticatedOSMAPWSTGRunner().verify_logout_boundary(
        boundary=_boundary(),
        logout_route="/logout",
        post_logout_route="/account/settings",
        status=LogoutCheckStatus.BLOCKED,
    )

    assert payload["cleanup_recorded"] is True
    assert payload["session_material_stored"] is False
