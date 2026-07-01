"""Generate in-scope WSTG objectives from scope and ROE."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from aotp.roe import RulesOfEngagement

from .strategy_map import ExecutableFamily, WSTGPhase, WSTGStrategyEntry, WSTGStrategyMap


class WSTGObjectiveError(ValueError):
    """Raised when a WSTG objective cannot be generated safely."""


@dataclass(frozen=True)
class WSTGCampaignScope:
    campaign_id: str
    target_alias: str
    base_url: str
    authorization_reference: str
    operator_approved: bool
    allowed_phases: frozenset[WSTGPhase]
    approved_families: frozenset[ExecutableFamily]
    authenticated: bool = False
    allow_session_material: bool = False
    allow_input_boundary: bool = False
    allow_browser: bool = True
    allow_active_validation: bool = False
    max_objectives: int = 20

    def __post_init__(self) -> None:
        for field_name, value in (
            ("campaign_id", self.campaign_id),
            ("target_alias", self.target_alias),
        ):
            if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", value) is None:
                raise WSTGObjectiveError(f"{field_name} must be a safe lowercase identifier")
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise WSTGObjectiveError("base_url must be an absolute http or https URL")
        if parsed.username is not None or parsed.password is not None:
            raise WSTGObjectiveError("base_url credentials are not allowed")
        if parsed.query or parsed.fragment:
            raise WSTGObjectiveError("base_url query and fragment are not allowed")
        if not self.authorization_reference.strip():
            raise WSTGObjectiveError("authorization_reference is required")
        if not self.operator_approved:
            raise WSTGObjectiveError("operator approval is required")
        if not self.allowed_phases:
            raise WSTGObjectiveError("at least one WSTG phase must be allowed")
        if not self.approved_families:
            raise WSTGObjectiveError("at least one executable family must be approved")
        if self.max_objectives < 1:
            raise WSTGObjectiveError("max_objectives must be positive")

    @property
    def origin(self) -> str:
        parsed = urlsplit(self.base_url)
        default_port = 443 if parsed.scheme == "https" else 80
        suffix = f":{parsed.port}" if parsed.port and parsed.port != default_port else ""
        return f"{parsed.scheme}://{parsed.hostname}{suffix}"

    @property
    def host(self) -> str:
        hostname = urlsplit(self.base_url).hostname
        if hostname is None:
            raise WSTGObjectiveError("base_url host is missing")
        return hostname

    @property
    def port(self) -> int:
        parsed = urlsplit(self.base_url)
        return parsed.port or (443 if parsed.scheme == "https" else 80)

    @classmethod
    def from_roe(
        cls,
        roe: RulesOfEngagement,
        *,
        base_url: str,
        allowed_phases: frozenset[WSTGPhase] | None = None,
        approved_families: frozenset[ExecutableFamily] | None = None,
        authenticated: bool = False,
        allow_session_material: bool = False,
        allow_input_boundary: bool = False,
        allow_browser: bool = True,
        allow_active_validation: bool = False,
        max_objectives: int = 20,
    ) -> "WSTGCampaignScope":
        return cls(
            campaign_id=roe.campaign_id,
            target_alias=roe.target_alias,
            base_url=base_url,
            authorization_reference=roe.authorization_reference,
            operator_approved=roe.operator_approved,
            allowed_phases=allowed_phases
            or frozenset({WSTGPhase.PASSIVE, WSTGPhase.BROWSER, WSTGPhase.REPORT}),
            approved_families=approved_families
            or frozenset(ExecutableFamily(tool_name) for tool_name in roe.allowed_tool_names if _is_family(tool_name)),
            authenticated=authenticated,
            allow_session_material=allow_session_material,
            allow_input_boundary=allow_input_boundary,
            allow_browser=allow_browser,
            allow_active_validation=allow_active_validation,
            max_objectives=max_objectives,
        )


@dataclass(frozen=True)
class WSTGObjective:
    objective_id: str
    campaign_id: str
    target_alias: str
    wstg_id: str
    phase: WSTGPhase
    family: ExecutableFamily
    tool_name: str
    arguments: dict[str, Any]
    risk_tier: str
    evidence_classification: str
    evidence_required: tuple[str, ...]
    requires_human_approval: bool
    rationale: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "campaign_id": self.campaign_id,
            "target_alias": self.target_alias,
            "wstg_id": self.wstg_id,
            "phase": self.phase.value,
            "family": self.family.value,
            "tool_name": self.tool_name,
            "arguments": dict(self.arguments),
            "risk_tier": self.risk_tier,
            "evidence_classification": self.evidence_classification,
            "evidence_required": list(self.evidence_required),
            "requires_human_approval": self.requires_human_approval,
            "rationale": self.rationale,
        }


def generate_wstg_objectives(
    scope: WSTGCampaignScope,
    strategy_map: WSTGStrategyMap,
    *,
    roe: RulesOfEngagement | None = None,
) -> tuple[WSTGObjective, ...]:
    """Generate approved WSTG objectives without executing tools or expanding scope."""

    objectives: list[WSTGObjective] = []
    for entry in strategy_map.entries():
        if len(objectives) >= scope.max_objectives:
            break
        if not _entry_allowed(entry, scope):
            continue
        arguments = _arguments_for(entry, scope)
        if roe is not None:
            reasons = _roe_reasons(entry, arguments, roe)
            if reasons:
                continue
        objective_id = _objective_id(entry)
        objectives.append(
            WSTGObjective(
                objective_id=objective_id,
                campaign_id=scope.campaign_id,
                target_alias=scope.target_alias,
                wstg_id=entry.wstg_id,
                phase=entry.phase,
                family=entry.family,
                tool_name=entry.tool_name,
                arguments=arguments,
                risk_tier=entry.risk_tier.value,
                evidence_classification=entry.evidence_classification,
                evidence_required=entry.evidence_required,
                requires_human_approval=entry.requires_human_approval,
                rationale=f"{entry.wstg_id} maps to {entry.phase.value} phase via {entry.family.value}",
            )
        )
    return tuple(objectives)


def _is_family(value: str) -> bool:
    try:
        ExecutableFamily(value)
    except ValueError:
        return False
    return True


def _entry_allowed(entry: WSTGStrategyEntry, scope: WSTGCampaignScope) -> bool:
    if entry.phase not in scope.allowed_phases:
        return False
    if entry.family not in scope.approved_families:
        return False
    if entry.phase is WSTGPhase.BROWSER and not scope.allow_browser:
        return False
    if entry.family is ExecutableFamily.AUTH_BOUNDARY and not scope.authenticated:
        return False
    if entry.family is ExecutableFamily.SESSION_MANAGEMENT and not scope.allow_session_material:
        return False
    if entry.family is ExecutableFamily.INPUT_BOUNDARY and not scope.allow_input_boundary:
        return False
    if entry.phase is WSTGPhase.VALIDATION and not scope.allow_active_validation:
        return False
    return True


def _arguments_for(entry: WSTGStrategyEntry, scope: WSTGCampaignScope) -> dict[str, Any]:
    if entry.family is ExecutableFamily.HTTP_METADATA:
        return {"url": scope.origin + "/"}
    if entry.family is ExecutableFamily.WELL_KNOWN_TEXT:
        return {"base_url": scope.origin}
    if entry.family is ExecutableFamily.TLS_METADATA:
        return {"host": scope.host, "port": scope.port, "server_name": scope.host}
    if entry.family is ExecutableFamily.PLAYWRIGHT_PASSIVE_METADATA:
        return {"url": scope.origin + "/"}
    if entry.family is ExecutableFamily.ZAP_PASSIVE_BASELINE:
        return {"target_url": scope.origin + "/", **entry.default_arguments}
    return {
        "target_alias": scope.target_alias,
        "base_url": scope.origin,
        "wstg_id": entry.wstg_id,
        **entry.default_arguments,
    }


def _roe_reasons(entry: WSTGStrategyEntry, arguments: dict[str, Any], roe: RulesOfEngagement) -> tuple[str, ...]:
    reasons: list[str] = []
    if not (roe.allows_tool_name(entry.tool_name) or roe.allows_tool_name(entry.family.value)):
        reasons.append("tool or executable family is not allowed by ROE")
    if not roe.allows_risk_tier(entry.risk_tier):
        reasons.append("risk tier is not allowed by ROE")
    if entry.evidence_classification not in roe.evidence_classifications:
        reasons.append("evidence classification is not allowed by ROE")
    for key in ("url", "base_url", "target_url"):
        if key in arguments:
            allowed, reason = roe.allows_url(str(arguments[key]))
            if not allowed:
                reasons.append(reason)
    if "host" in arguments and not roe.allows_host(str(arguments["host"])):
        reasons.append("host is outside ROE scope")
    if "port" in arguments and isinstance(arguments["port"], int) and not roe.allows_port(arguments["port"]):
        reasons.append("port is outside ROE scope")
    return tuple(reasons)


def _objective_id(entry: WSTGStrategyEntry) -> str:
    return entry.wstg_id.lower().replace("-", "_")
