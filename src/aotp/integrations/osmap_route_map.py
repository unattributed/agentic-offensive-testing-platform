"""Route and authentication maps derived from safe OSMAP source metadata."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable

from .osmap_source_review import SourceReviewResult, SourceRouteCandidate


class OSMAPRouteMapError(ValueError):
    """Raised when source-derived route metadata cannot be mapped safely."""


@dataclass(frozen=True)
class RouteMapEntry:
    route_id: str
    method: str
    path_pattern: str
    handler_reference: str
    auth_required: bool
    auth_mechanism_hint: str
    auth_hints: tuple[str, ...]
    source_reference: str
    confidence: str
    evidence_hash_references: tuple[str, ...]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "method": self.method,
            "path_pattern": self.path_pattern,
            "handler_reference": self.handler_reference,
            "auth_required": self.auth_required,
            "auth_mechanism_hint": self.auth_mechanism_hint,
            "auth_hints": list(self.auth_hints),
            "source_reference": self.source_reference,
            "confidence": self.confidence,
            "evidence_hash_references": list(self.evidence_hash_references),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class AuthMap:
    login_route_candidates: tuple[str, ...]
    logout_route_candidates: tuple[str, ...]
    session_validation_candidates: tuple[str, ...]
    privileged_route_candidates: tuple[str, ...]
    unauthenticated_route_candidates: tuple[str, ...]
    csrf_related_route_hints: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "login_route_candidates": list(self.login_route_candidates),
            "logout_route_candidates": list(self.logout_route_candidates),
            "session_validation_candidates": list(self.session_validation_candidates),
            "privileged_route_candidates": list(self.privileged_route_candidates),
            "unauthenticated_route_candidates": list(self.unauthenticated_route_candidates),
            "csrf_related_route_hints": list(self.csrf_related_route_hints),
        }


@dataclass(frozen=True)
class OSMAPRouteAuthMap:
    source_root_hash: str
    routes: tuple[RouteMapEntry, ...]
    auth_map: AuthMap
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "source_root_hash": self.source_root_hash,
            "routes": [route.as_dict() for route in self.routes],
            "auth_map": self.auth_map.as_dict(),
            "limitations": list(self.limitations),
            "redacted": True,
        }


def build_osmap_route_auth_map(review: SourceReviewResult) -> OSMAPRouteAuthMap:
    """Build deterministic route and auth maps from safe source review metadata."""

    seen: dict[tuple[str, str], SourceRouteCandidate] = {}
    for candidate in review.route_candidates:
        key = (candidate.method.upper(), candidate.path_pattern)
        seen.setdefault(key, candidate)
    routes = tuple(_entry_from_candidate(candidate) for _, candidate in sorted(seen.items()))
    auth_map = _auth_map_from_routes(routes)
    limitations = (
        "source hints are not vulnerability findings",
        "routes require governed authenticated execution before candidate findings",
    )
    return OSMAPRouteAuthMap(
        source_root_hash=review.source_root_hash,
        routes=routes,
        auth_map=auth_map,
        limitations=limitations,
    )


def _entry_from_candidate(candidate: SourceRouteCandidate) -> RouteMapEntry:
    hints = set(candidate.auth_hints)
    path_lower = candidate.path_pattern.lower()
    auth_required = bool(hints & {"require_auth", "authenticated", "session", "cookie", "bearer"})
    if "login" in hints or "login" in path_lower:
        mechanism = "login"
    elif "logout" in hints or "logout" in path_lower:
        mechanism = "logout"
        auth_required = True
    elif "csrf" in hints:
        mechanism = "csrf"
    elif auth_required:
        mechanism = "session"
    else:
        mechanism = "unknown"
    route_id = _route_id(candidate.method, candidate.path_pattern)
    return RouteMapEntry(
        route_id=route_id,
        method=candidate.method.upper(),
        path_pattern=candidate.path_pattern,
        handler_reference=candidate.handler_reference,
        auth_required=auth_required,
        auth_mechanism_hint=mechanism,
        auth_hints=tuple(sorted(hints)),
        source_reference=candidate.source_reference,
        confidence=candidate.confidence,
        evidence_hash_references=(candidate.evidence_sha256,),
        limitations=("source-derived route hint only",),
    )


def _auth_map_from_routes(routes: Iterable[RouteMapEntry]) -> AuthMap:
    login: list[str] = []
    logout: list[str] = []
    session: list[str] = []
    privileged: list[str] = []
    unauth: list[str] = []
    csrf: list[str] = []
    for route in routes:
        route_text = f"{route.path_pattern} {route.auth_mechanism_hint} {' '.join(route.auth_hints)}".lower()
        if "login" in route_text:
            login.append(route.route_id)
        if "logout" in route_text:
            logout.append(route.route_id)
        if route.auth_required:
            session.append(route.route_id)
        else:
            unauth.append(route.route_id)
        if any(part in route_text for part in ("admin", "manage", "settings", "account")):
            privileged.append(route.route_id)
        if "csrf" in route_text:
            csrf.append(route.route_id)
    return AuthMap(
        login_route_candidates=tuple(login),
        logout_route_candidates=tuple(logout),
        session_validation_candidates=tuple(session),
        privileged_route_candidates=tuple(privileged),
        unauthenticated_route_candidates=tuple(unauth),
        csrf_related_route_hints=tuple(csrf),
    )


def _route_id(method: str, path_pattern: str) -> str:
    digest = hashlib.sha256(f"{method.upper()} {path_pattern}".encode("utf-8")).hexdigest()[:12]
    return f"route-{digest}"
