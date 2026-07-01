"""Documented risk tiers for governed native campaign tools."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ToolRiskTier(StrEnum):
    """Ordered risk tiers used by the native tool registry."""

    PASSIVE_METADATA = "passive_metadata"
    PASSIVE_BROWSER = "passive_browser"
    PASSIVE_SCANNER = "passive_scanner"
    SERVICE_FINGERPRINT = "service_fingerprint"
    AUTHENTICATED_SAFE = "authenticated_safe"
    INTRUSIVE_VALIDATION = "intrusive_validation"
    EXPLOITATION_VALIDATION = "exploitation_validation"


@dataclass(frozen=True)
class RiskTierDefinition:
    tier: ToolRiskTier
    rank: int
    summary: str
    requires_human_approval: bool
    default_evidence_classification: str


RISK_TIER_DEFINITIONS: dict[ToolRiskTier, RiskTierDefinition] = {
    ToolRiskTier.PASSIVE_METADATA: RiskTierDefinition(
        tier=ToolRiskTier.PASSIVE_METADATA,
        rank=10,
        summary="credential-free metadata observation, no crawling, no mutation",
        requires_human_approval=False,
        default_evidence_classification="public",
    ),
    ToolRiskTier.PASSIVE_BROWSER: RiskTierDefinition(
        tier=ToolRiskTier.PASSIVE_BROWSER,
        rank=20,
        summary="single-page browser observation without form submission or interaction",
        requires_human_approval=False,
        default_evidence_classification="public",
    ),
    ToolRiskTier.PASSIVE_SCANNER: RiskTierDefinition(
        tier=ToolRiskTier.PASSIVE_SCANNER,
        rank=30,
        summary="bounded passive scanner execution, including passive spidering only",
        requires_human_approval=False,
        default_evidence_classification="restricted",
    ),
    ToolRiskTier.SERVICE_FINGERPRINT: RiskTierDefinition(
        tier=ToolRiskTier.SERVICE_FINGERPRINT,
        rank=40,
        summary="single-service fingerprinting that can create target-visible traffic",
        requires_human_approval=True,
        default_evidence_classification="restricted",
    ),
    ToolRiskTier.AUTHENTICATED_SAFE: RiskTierDefinition(
        tier=ToolRiskTier.AUTHENTICATED_SAFE,
        rank=50,
        summary="authorized authenticated observation without state change",
        requires_human_approval=True,
        default_evidence_classification="restricted",
    ),
    ToolRiskTier.INTRUSIVE_VALIDATION: RiskTierDefinition(
        tier=ToolRiskTier.INTRUSIVE_VALIDATION,
        rank=60,
        summary="bounded validation with elevated target or application risk",
        requires_human_approval=True,
        default_evidence_classification="restricted",
    ),
    ToolRiskTier.EXPLOITATION_VALIDATION: RiskTierDefinition(
        tier=ToolRiskTier.EXPLOITATION_VALIDATION,
        rank=70,
        summary="explicitly approved exploitation validation or proof construction",
        requires_human_approval=True,
        default_evidence_classification="secret",
    ),
}


def parse_risk_tier(value: str | ToolRiskTier) -> ToolRiskTier:
    """Return a risk tier or fail closed on unknown values."""

    if isinstance(value, ToolRiskTier):
        return value
    try:
        return ToolRiskTier(str(value))
    except ValueError as exc:
        raise ValueError(f"unsupported native tool risk tier: {value}") from exc


def risk_tier_definition(value: str | ToolRiskTier) -> RiskTierDefinition:
    """Return the documented definition for a risk tier."""

    return RISK_TIER_DEFINITIONS[parse_risk_tier(value)]


def risk_tier_rank(value: str | ToolRiskTier) -> int:
    """Return the deterministic rank used for ordering and policy comparison."""

    return risk_tier_definition(value).rank


def risk_tier_within_maximum(
    value: str | ToolRiskTier,
    maximum: str | ToolRiskTier,
) -> bool:
    """Return whether a tier is at or below a configured maximum tier."""

    return risk_tier_rank(value) <= risk_tier_rank(maximum)
