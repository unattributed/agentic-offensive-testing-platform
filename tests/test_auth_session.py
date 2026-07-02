from datetime import datetime, timedelta, timezone

import pytest

from aotp.auth_session import (
    AllowedRoute,
    AuthSessionError,
    AuthState,
    AuthenticatedSessionBoundary,
    LogoutCheckStatus,
)


DIGEST = "a" * 64


def _future():
    return (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()


def _boundary(**overrides):
    values = dict(
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
        allowed_routes=(AllowedRoute("/account/*", frozenset({"GET"})), AllowedRoute("/logout", frozenset({"POST"}))),
        allowed_auth_states=frozenset({AuthState.AUTHENTICATED, AuthState.POST_LOGOUT}),
    )
    values.update(overrides)
    return AuthenticatedSessionBoundary(**values)


def test_authenticated_boundary_allows_explicit_route_scope():
    boundary = _boundary()

    decision = boundary.authorize_route(
        method="GET",
        path="/account/settings",
        target_alias="owned-app",
        account_alias="account-one",
    )

    assert decision.allowed is True
    assert boundary.as_public_dict()["scope_binding"]


def test_authenticated_boundary_denies_missing_permission_or_scope_mismatch():
    with pytest.raises(AuthSessionError):
        _boundary(approved_permissions=frozenset())
    with pytest.raises(AuthSessionError):
        _boundary(approval_scope_sha256="b" * 64)


def test_authenticated_boundary_denies_cross_target_account_and_route():
    boundary = _boundary()

    with pytest.raises(AuthSessionError):
        boundary.authorize_route(method="GET", path="/account/settings", target_alias="other", account_alias="account-one")
    with pytest.raises(AuthSessionError):
        boundary.authorize_route(method="GET", path="/account/settings", target_alias="owned-app", account_alias="other")
    with pytest.raises(AuthSessionError):
        boundary.authorize_route(method="GET", path="/admin", target_alias="owned-app", account_alias="account-one")


def test_logout_boundary_records_cleanup_without_session_material():
    boundary = _boundary()

    record = boundary.record_logout_boundary(
        logout_route="/logout",
        post_logout_route="/account/settings",
        status=LogoutCheckStatus.BLOCKED,
        cleanup_recorded=True,
    )

    public = record.as_dict()
    assert public["cleanup_recorded"] is True
    assert public["session_material_stored"] is False


def test_logout_boundary_fails_closed_for_unknown_logout_route():
    boundary = _boundary()

    with pytest.raises(AuthSessionError):
        boundary.record_logout_boundary(
            logout_route="/not-logout",
            post_logout_route="/account/settings",
            status=LogoutCheckStatus.BLOCKED,
            cleanup_recorded=True,
        )
