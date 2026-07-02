"""Map OSMAP route metadata into Sprint 17F WSTG execution requests."""

from __future__ import annotations

from dataclasses import dataclass

from aotp.wstg.execution_adapter import WSTGAdapterKind, WSTGExecutionRequest, build_execution_request
from aotp.wstg.objective_generator import WSTGCampaignScope, WSTGObjective
from aotp.wstg.strategy_map import ExecutableFamily, WSTGPhase

from .osmap_route_map import OSMAPRouteAuthMap, RouteMapEntry


class OSMAPWSTGMappingError(ValueError):
    """Raised when OSMAP hints cannot become governed WSTG requests."""


@dataclass(frozen=True)
class OSMAPWSTGCandidate:
    route_id: str
    request: WSTGExecutionRequest
    source_limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "request": self.request.as_dict(),
            "source_limitations": list(self.source_limitations),
            "redacted": True,
        }


def map_osmap_routes_to_wstg_requests(
    route_map: OSMAPRouteAuthMap,
    scope: WSTGCampaignScope,
    *,
    approval_reference: str,
    execution_mode: str = "dry_run",
) -> tuple[OSMAPWSTGCandidate, ...]:
    """Convert source-derived route hints into adapter requests.

    The resulting requests do not authorize execution by themselves. They still
    require the authenticated session boundary and governed runner checks.
    """

    if not scope.authenticated:
        raise OSMAPWSTGMappingError("OSMAP authenticated candidates require authenticated WSTG scope")
    if not scope.allow_session_material:
        raise OSMAPWSTGMappingError("OSMAP authenticated candidates require session material permission")
    if WSTGPhase.AUTH not in scope.allowed_phases:
        raise OSMAPWSTGMappingError("AUTH phase is not allowed by scope")
    if not approval_reference.strip():
        raise OSMAPWSTGMappingError("approval reference is required")
    candidates: list[OSMAPWSTGCandidate] = []
    for route in route_map.routes:
        family = _family_for_route(route)
        if family not in scope.approved_families:
            continue
        objective = WSTGObjective(
            objective_id=f"osmap_{route.route_id.replace('-', '_')}",
            campaign_id=scope.campaign_id,
            target_alias=scope.target_alias,
            wstg_id="WSTG-v42-ATHN-01" if family is ExecutableFamily.AUTH_BOUNDARY else "WSTG-v42-SESS-02",
            phase=WSTGPhase.AUTH,
            family=family,
            tool_name="osmap_authenticated_wstg",
            arguments={
                "target_alias": scope.target_alias,
                "route_id": route.route_id,
                "method": route.method,
                "path_pattern": route.path_pattern,
                "auth_required": route.auth_required,
                "auth_mechanism_hint": route.auth_mechanism_hint,
                "source_reference": route.source_reference,
                "evidence_hash_references": list(route.evidence_hash_references),
            },
            risk_tier="passive_metadata",
            evidence_classification="restricted",
            evidence_required=("auth_route_observation", "redacted_session_metadata"),
            requires_human_approval=True,
            rationale="OSMAP source-derived route hint mapped through Sprint 17F adapter contract",
        )
        request = build_execution_request(
            objective,
            adapter_kind=WSTGAdapterKind.APP_SPECIFIC_RUNNER,
            executor_name="osmap_authenticated_wstg",
            approval_reference=approval_reference,
            request_budget=1,
            execution_mode=execution_mode,
        )
        candidates.append(
            OSMAPWSTGCandidate(
                route_id=route.route_id,
                request=request,
                source_limitations=route.limitations + ("hint does not create finding",),
            )
        )
    return tuple(candidates)


def _family_for_route(route: RouteMapEntry) -> ExecutableFamily:
    if route.auth_mechanism_hint in {"login", "logout"}:
        return ExecutableFamily.AUTH_BOUNDARY
    return ExecutableFamily.SESSION_MANAGEMENT
