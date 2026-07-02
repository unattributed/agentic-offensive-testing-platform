"""Authenticated session boundary models for governed campaign work."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AuthSessionError(ValueError):
    """Raised when authenticated session use is not authorized."""


class AuthState(str, Enum):
    UNAUTHENTICATED = "unauthenticated"
    AUTHENTICATED = "authenticated"
    POST_LOGOUT = "post_logout"


class LogoutCheckStatus(str, Enum):
    BLOCKED = "blocked"
    STILL_AUTHENTICATED = "still_authenticated"
    INCONCLUSIVE = "inconclusive"
    SKIPPED = "skipped"
    DENIED = "denied"


_ALIAS_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")
_SAFE_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}


@dataclass(frozen=True)
class AllowedRoute:
    """One explicit route boundary for authenticated work."""

    path_pattern: str
    methods: frozenset[str] = field(default_factory=lambda: frozenset({"GET"}))

    def __post_init__(self) -> None:
        _validate_path_pattern(self.path_pattern)
        normalized = frozenset(method.upper() for method in self.methods)
        if not normalized or any(method not in _SAFE_METHODS for method in normalized):
            raise AuthSessionError("allowed route methods are unsafe")
        object.__setattr__(self, "methods", normalized)

    def matches(self, method: str, path: str) -> bool:
        normalized_method = method.upper()
        if normalized_method not in self.methods:
            return False
        _validate_route_path(path)
        if self.path_pattern.endswith("/*"):
            prefix = self.path_pattern[:-1]
            return path.startswith(prefix)
        return path == self.path_pattern

    def as_dict(self) -> dict[str, object]:
        return {"path_pattern": self.path_pattern, "methods": sorted(self.methods)}


@dataclass(frozen=True)
class AuthenticatedRouteDecision:
    allowed: bool
    route_path: str
    method: str
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "route_path": self.route_path,
            "method": self.method,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class LogoutBoundaryRecord:
    campaign_id: str
    account_alias: str
    logout_route: str
    post_logout_route: str
    status: LogoutCheckStatus
    cleanup_recorded: bool
    session_material_stored: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_alias(self.campaign_id, "campaign_id")
        _safe_alias(self.account_alias, "account_alias")
        _validate_route_path(self.logout_route)
        _validate_route_path(self.post_logout_route)
        if self.session_material_stored:
            raise AuthSessionError("logout records must not store raw session material")

    def as_dict(self) -> dict[str, object]:
        return {
            "campaign_id": self.campaign_id,
            "account_alias": self.account_alias,
            "logout_route": self.logout_route,
            "post_logout_route": self.post_logout_route,
            "status": self.status.value,
            "cleanup_recorded": self.cleanup_recorded,
            "session_material_stored": self.session_material_stored,
            "notes": list(self.notes),
            "redacted": True,
        }


@dataclass(frozen=True)
class AuthenticatedSessionBoundary:
    """Authorization-bound account and route scope for authenticated checks."""

    campaign_id: str
    operator_alias: str
    target_alias: str
    account_alias: str
    authorization_reference: str
    approval_reference: str
    rules_of_engagement_reference: str
    scope_sha256: str
    approval_scope_sha256: str
    approval_operator_alias: str
    approval_expires_utc: str
    approved_permissions: frozenset[str]
    allowed_routes: tuple[AllowedRoute, ...]
    allowed_auth_states: frozenset[AuthState] = field(default_factory=lambda: frozenset({AuthState.AUTHENTICATED}))
    storage_policy: str = "public_metadata_only"
    evidence_classification: str = "restricted"
    active: bool = True
    service_alias: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("campaign_id", self.campaign_id),
            ("operator_alias", self.operator_alias),
            ("target_alias", self.target_alias),
            ("account_alias", self.account_alias),
        ):
            _safe_alias(value, field_name)
        if self.service_alias is not None:
            _safe_alias(self.service_alias, "service_alias")
        for field_name, value in (
            ("authorization_reference", self.authorization_reference),
            ("approval_reference", self.approval_reference),
            ("rules_of_engagement_reference", self.rules_of_engagement_reference),
        ):
            if not isinstance(value, str) or not value.strip():
                raise AuthSessionError(f"{field_name} is required")
        for field_name, value in (("scope_sha256", self.scope_sha256), ("approval_scope_sha256", self.approval_scope_sha256)):
            if _DIGEST_RE.fullmatch(value) is None:
                raise AuthSessionError(f"{field_name} must be a lowercase SHA256 digest")
        if self.scope_sha256 != self.approval_scope_sha256:
            raise AuthSessionError("approval does not match scope digest")
        if self.operator_alias != self.approval_operator_alias:
            raise AuthSessionError("approval does not match operator")
        if "authenticated_testing" not in self.approved_permissions:
            raise AuthSessionError("approval is missing authenticated_testing permission")
        if not self.allowed_routes:
            raise AuthSessionError("at least one authenticated route must be allowed")
        if not self.allowed_auth_states:
            raise AuthSessionError("at least one auth state must be allowed")
        _parse_future_utc(self.approval_expires_utc)
        if self.storage_policy not in {"vaulted", "memory_only", "do_not_store", "public_metadata_only"}:
            raise AuthSessionError("unsupported authenticated storage policy")
        if self.evidence_classification not in {"public", "restricted", "poc_sensitive", "recipient_only"}:
            raise AuthSessionError("unsupported evidence classification")

    @property
    def scope_binding(self) -> str:
        text = "\n".join(
            [
                self.campaign_id,
                self.operator_alias,
                self.target_alias,
                self.account_alias,
                self.authorization_reference,
                self.approval_reference,
                self.rules_of_engagement_reference,
                self.scope_sha256,
            ]
        )
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def assert_active(self) -> None:
        if not self.active:
            raise AuthSessionError("authenticated session boundary is inactive")
        _parse_future_utc(self.approval_expires_utc)

    def authorize_route(
        self,
        *,
        method: str,
        path: str,
        target_alias: str,
        account_alias: str,
        auth_state: AuthState | str = AuthState.AUTHENTICATED,
    ) -> AuthenticatedRouteDecision:
        """Fail closed unless route, target, account, and auth state match the boundary."""

        reasons: list[str] = []
        try:
            self.assert_active()
        except AuthSessionError as exc:
            reasons.append(str(exc))
        if target_alias != self.target_alias:
            reasons.append("target alias crosses authenticated session boundary")
        if account_alias != self.account_alias:
            reasons.append("account alias crosses authenticated session boundary")
        parsed_state = AuthState(auth_state)
        if parsed_state not in self.allowed_auth_states:
            reasons.append("auth state is not allowed by boundary")
        route_allowed = any(route.matches(method, path) for route in self.allowed_routes)
        if not route_allowed:
            reasons.append("route is outside authenticated route scope")
        decision = AuthenticatedRouteDecision(
            allowed=not reasons,
            route_path=path,
            method=method.upper(),
            reasons=tuple(reasons or ("allowed",)),
        )
        if not decision.allowed:
            raise AuthSessionError("; ".join(decision.reasons))
        return decision

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "operator_alias": self.operator_alias,
            "target_alias": self.target_alias,
            "account_alias": self.account_alias,
            "authorization_reference": self.authorization_reference,
            "approval_reference": self.approval_reference,
            "rules_of_engagement_reference": self.rules_of_engagement_reference,
            "scope_sha256": self.scope_sha256,
            "approval_expires_utc": self.approval_expires_utc,
            "approved_permissions": sorted(self.approved_permissions),
            "allowed_routes": [route.as_dict() for route in self.allowed_routes],
            "allowed_auth_states": sorted(state.value for state in self.allowed_auth_states),
            "storage_policy": self.storage_policy,
            "evidence_classification": self.evidence_classification,
            "active": self.active,
            "service_alias": self.service_alias,
            "scope_binding": self.scope_binding,
            "redacted": True,
        }

    def record_logout_boundary(
        self,
        *,
        logout_route: str,
        post_logout_route: str,
        status: LogoutCheckStatus | str,
        cleanup_recorded: bool,
        notes: tuple[str, ...] = (),
    ) -> LogoutBoundaryRecord:
        self.authorize_route(
            method="POST",
            path=logout_route,
            target_alias=self.target_alias,
            account_alias=self.account_alias,
            auth_state=AuthState.AUTHENTICATED,
        )
        if status in {LogoutCheckStatus.BLOCKED, "blocked"}:
            post_state = AuthState.POST_LOGOUT
        else:
            post_state = AuthState.AUTHENTICATED
        self.authorize_route(
            method="GET",
            path=post_logout_route,
            target_alias=self.target_alias,
            account_alias=self.account_alias,
            auth_state=post_state,
        )
        return LogoutBoundaryRecord(
            campaign_id=self.campaign_id,
            account_alias=self.account_alias,
            logout_route=logout_route,
            post_logout_route=post_logout_route,
            status=LogoutCheckStatus(status),
            cleanup_recorded=cleanup_recorded,
            notes=notes,
        )


def _parse_future_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuthSessionError("approval expiry must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise AuthSessionError("approval expiry must include timezone")
    if parsed.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise AuthSessionError("approval is expired")
    return parsed


def _safe_alias(value: str, field: str) -> str:
    if not isinstance(value, str) or _ALIAS_RE.fullmatch(value) is None:
        raise AuthSessionError(f"{field} must be a safe lowercase alias")
    return value


def _validate_path_pattern(value: str) -> None:
    if not isinstance(value, str) or not value.startswith("/"):
        raise AuthSessionError("route path patterns must start with slash")
    if ".." in value or "\\" in value or any(character in value for character in "\n\r\t"):
        raise AuthSessionError("route path pattern is unsafe")
    if "*" in value and not value.endswith("/*"):
        raise AuthSessionError("wildcards are allowed only as trailing /*")


def _validate_route_path(value: str) -> None:
    if not isinstance(value, str) or not value.startswith("/"):
        raise AuthSessionError("route path must start with slash")
    if ".." in value or "\\" in value or "*" in value or any(character in value for character in "\n\r\t"):
        raise AuthSessionError("route path is unsafe")
