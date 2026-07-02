"""Session material classification helpers for authenticated checks."""

from __future__ import annotations

from enum import Enum


class SessionMaterialKind(str, Enum):
    COOKIE = "cookie"
    CSRF = "csrf"
    BEARER_TOKEN = "bearer_token"
    SESSION_IDENTIFIER = "session_identifier"
    POST_LOGIN_MARKER = "post_login_marker"
    LOGOUT_MARKER = "logout_marker"
    POST_LOGOUT_CHECK = "post_logout_check"


def material_default_classification(kind: SessionMaterialKind | str) -> str:
    parsed = SessionMaterialKind(kind)
    if parsed in {
        SessionMaterialKind.COOKIE,
        SessionMaterialKind.CSRF,
        SessionMaterialKind.BEARER_TOKEN,
        SessionMaterialKind.SESSION_IDENTIFIER,
    }:
        return "secret"
    return "restricted"
