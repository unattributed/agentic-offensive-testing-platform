"""Version-aware WSTG strategy map for campaign objective generation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from aotp.tool_risk_tiers import ToolRiskTier, parse_risk_tier

from .catalog import WSTG_V42_CATALOG, WSTGCatalogError


class WSTGStrategyError(ValueError):
    """Raised when a WSTG strategy entry or map is invalid."""


class WSTGPhase(str, Enum):
    """AOTP campaign phase assigned to a WSTG objective."""

    PASSIVE = "passive"
    BROWSER = "browser"
    AUTH = "auth"
    INPUT = "input"
    VALIDATION = "validation"
    REPORT = "report"


class ExecutableFamily(str, Enum):
    """Governed execution family used by the agent when selecting objectives."""

    HTTP_METADATA = "http_metadata"
    TLS_METADATA = "tls_metadata"
    WELL_KNOWN_TEXT = "well_known_text"
    PLAYWRIGHT_PASSIVE_METADATA = "playwright_passive_metadata"
    ZAP_PASSIVE_BASELINE = "zap_passive_baseline"
    AUTH_BOUNDARY = "auth_boundary"
    SESSION_MANAGEMENT = "session_management"
    ERROR_HANDLING = "error_handling"
    INPUT_BOUNDARY = "input_boundary"
    COVERAGE_REPORT = "coverage_report"


_PHASE_ORDER = {
    WSTGPhase.PASSIVE: 0,
    WSTGPhase.BROWSER: 1,
    WSTGPhase.AUTH: 2,
    WSTGPhase.INPUT: 3,
    WSTGPhase.VALIDATION: 4,
    WSTGPhase.REPORT: 5,
}
_WSTG_ID_RE = re.compile(r"^WSTG-v[0-9]+-[A-Z]{4}-[0-9]{2}$")


def phase_order_index(phase: WSTGPhase | str) -> int:
    """Return deterministic campaign phase order for WSTG objective selection."""

    return _PHASE_ORDER[WSTGPhase(phase)]


@dataclass(frozen=True)
class WSTGStrategyEntry:
    """One WSTG mapping entry with execution and evidence metadata."""

    wstg_id: str
    version: str
    category: str
    name: str
    phase: WSTGPhase
    family: ExecutableFamily
    tool_name: str
    risk_tier: ToolRiskTier
    evidence_classification: str
    evidence_required: tuple[str, ...]
    requires_human_approval: bool = False
    default_arguments: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if _WSTG_ID_RE.fullmatch(self.wstg_id) is None:
            raise WSTGStrategyError("wstg_id must be version-qualified, for example WSTG-v42-INFO-02")
        if self.version not in self.wstg_id:
            raise WSTGStrategyError("entry version must appear in the WSTG identifier")
        if not self.category or len(self.category) != 4 or not self.category.isupper():
            raise WSTGStrategyError("WSTG category must be a four-character uppercase code")
        if not self.name.strip():
            raise WSTGStrategyError("WSTG entry name is required")
        parse_risk_tier(self.risk_tier)
        if self.evidence_classification not in {
            "public",
            "restricted",
            "secret",
            "poc_sensitive",
            "recipient_only",
        }:
            raise WSTGStrategyError("unsupported evidence classification")
        if not self.evidence_required:
            raise WSTGStrategyError("at least one evidence requirement is required")
        if self.version == "v42":
            try:
                catalog_case = WSTG_V42_CATALOG.by_id(self.wstg_id)
            except WSTGCatalogError as exc:
                raise WSTGStrategyError(str(exc)) from exc
            if catalog_case.category != self.category:
                raise WSTGStrategyError("strategy entry category must match the canonical WSTG catalog")
            if catalog_case.title != self.name:
                raise WSTGStrategyError("strategy entry name must match the canonical OWASP WSTG title")

    @property
    def sort_key(self) -> tuple[int, str]:
        return (_PHASE_ORDER[self.phase], self.wstg_id)

    def as_dict(self) -> dict[str, Any]:
        return {
            "wstg_id": self.wstg_id,
            "version": self.version,
            "category": self.category,
            "name": self.name,
            "phase": self.phase.value,
            "family": self.family.value,
            "tool_name": self.tool_name,
            "risk_tier": self.risk_tier.value,
            "evidence_classification": self.evidence_classification,
            "evidence_required": list(self.evidence_required),
            "requires_human_approval": self.requires_human_approval,
            "default_arguments": dict(self.default_arguments),
        }


class WSTGStrategyMap:
    """Immutable version-aware strategy map."""

    def __init__(self, entries: Iterable[WSTGStrategyEntry]) -> None:
        ordered = tuple(sorted(entries, key=lambda item: item.sort_key))
        if not ordered:
            raise WSTGStrategyError("at least one WSTG strategy entry is required")
        seen: set[str] = set()
        for entry in ordered:
            if entry.wstg_id in seen:
                raise WSTGStrategyError(f"duplicate WSTG identifier: {entry.wstg_id}")
            seen.add(entry.wstg_id)
        self._entries = ordered

    def entries(self) -> tuple[WSTGStrategyEntry, ...]:
        return self._entries

    def by_id(self, wstg_id: str) -> WSTGStrategyEntry:
        for entry in self._entries:
            if entry.wstg_id == wstg_id:
                return entry
        raise WSTGStrategyError(f"unknown WSTG identifier: {wstg_id}")

    def by_phase(self, phase: WSTGPhase | str) -> tuple[WSTGStrategyEntry, ...]:
        parsed = WSTGPhase(phase)
        return tuple(entry for entry in self._entries if entry.phase is parsed)

    def by_family(self, family: ExecutableFamily | str) -> tuple[WSTGStrategyEntry, ...]:
        parsed = ExecutableFamily(family)
        return tuple(entry for entry in self._entries if entry.family is parsed)

    def as_dict(self) -> dict[str, Any]:
        return {"entries": [entry.as_dict() for entry in self._entries]}


def build_default_strategy_map(version: str = "v42") -> WSTGStrategyMap:
    """Build the default AOTP WSTG v4.2 executable starter map.

    The map is deliberately smaller than the full catalog. It selects currently
    supported AOTP execution families from canonical OWASP WSTG v4.2 test cases.
    Coverage for every WSTG test belongs to :mod:`aotp.wstg.catalog` and
    :mod:`aotp.wstg.engine`; this function must not invent internal WSTG IDs or
    rename official OWASP tests.
    """

    entries = (
        WSTGStrategyEntry(
            wstg_id=f"WSTG-{version}-INFO-02",
            version=version,
            category="INFO",
            name="Fingerprint Web Server",
            phase=WSTGPhase.PASSIVE,
            family=ExecutableFamily.HTTP_METADATA,
            tool_name="http_metadata",
            risk_tier=ToolRiskTier.PASSIVE_METADATA,
            evidence_classification="public",
            evidence_required=("http_status", "headers", "server_metadata"),
        ),
        WSTGStrategyEntry(
            wstg_id=f"WSTG-{version}-INFO-03",
            version=version,
            category="INFO",
            name="Review Webserver Metafiles for Information Leakage",
            phase=WSTGPhase.PASSIVE,
            family=ExecutableFamily.WELL_KNOWN_TEXT,
            tool_name="well_known_text",
            risk_tier=ToolRiskTier.PASSIVE_METADATA,
            evidence_classification="public",
            evidence_required=("robots_txt", "security_txt"),
        ),
        WSTGStrategyEntry(
            wstg_id=f"WSTG-{version}-CRYP-01",
            version=version,
            category="CRYP",
            name="Testing for Weak Transport Layer Security",
            phase=WSTGPhase.PASSIVE,
            family=ExecutableFamily.TLS_METADATA,
            tool_name="tls_metadata",
            risk_tier=ToolRiskTier.PASSIVE_METADATA,
            evidence_classification="public",
            evidence_required=("tls_certificate_metadata", "transport_headers"),
        ),
        WSTGStrategyEntry(
            wstg_id=f"WSTG-{version}-INFO-06",
            version=version,
            category="INFO",
            name="Identify Application Entry Points",
            phase=WSTGPhase.BROWSER,
            family=ExecutableFamily.PLAYWRIGHT_PASSIVE_METADATA,
            tool_name="playwright_passive_metadata",
            risk_tier=ToolRiskTier.PASSIVE_BROWSER,
            evidence_classification="public",
            evidence_required=("final_url", "title", "forms", "links"),
        ),
        WSTGStrategyEntry(
            wstg_id=f"WSTG-{version}-ATHN-01",
            version=version,
            category="ATHN",
            name="Testing for Credentials Transported over an Encrypted Channel",
            phase=WSTGPhase.AUTH,
            family=ExecutableFamily.AUTH_BOUNDARY,
            tool_name="auth_boundary_check",
            risk_tier=ToolRiskTier.PASSIVE_METADATA,
            evidence_classification="restricted",
            evidence_required=("auth_route_observation", "transport_decision"),
            requires_human_approval=True,
        ),
        WSTGStrategyEntry(
            wstg_id=f"WSTG-{version}-SESS-02",
            version=version,
            category="SESS",
            name="Testing for Cookies Attributes",
            phase=WSTGPhase.AUTH,
            family=ExecutableFamily.SESSION_MANAGEMENT,
            tool_name="session_management_check",
            risk_tier=ToolRiskTier.PASSIVE_METADATA,
            evidence_classification="restricted",
            evidence_required=("cookie_attribute_names", "vault_handle_if_sensitive"),
            requires_human_approval=True,
        ),
        WSTGStrategyEntry(
            wstg_id=f"WSTG-{version}-ERRH-01",
            version=version,
            category="ERRH",
            name="Testing for Improper Error Handling",
            phase=WSTGPhase.INPUT,
            family=ExecutableFamily.ERROR_HANDLING,
            tool_name="error_handling_check",
            risk_tier=ToolRiskTier.PASSIVE_METADATA,
            evidence_classification="restricted",
            evidence_required=("bounded_error_observation", "stop_condition"),
        ),
        WSTGStrategyEntry(
            wstg_id=f"WSTG-{version}-INPV-04",
            version=version,
            category="INPV",
            name="Testing for HTTP Parameter Pollution",
            phase=WSTGPhase.INPUT,
            family=ExecutableFamily.INPUT_BOUNDARY,
            tool_name="input_boundary_check",
            risk_tier=ToolRiskTier.PASSIVE_METADATA,
            evidence_classification="restricted",
            evidence_required=("input_names", "allowed_payload_class", "request_budget"),
        ),
        WSTGStrategyEntry(
            wstg_id=f"WSTG-{version}-CONF-02",
            version=version,
            category="CONF",
            name="Test Application Platform Configuration",
            phase=WSTGPhase.VALIDATION,
            family=ExecutableFamily.ZAP_PASSIVE_BASELINE,
            tool_name="zap_passive_baseline",
            risk_tier=ToolRiskTier.PASSIVE_SCANNER,
            evidence_classification="restricted",
            evidence_required=("zap_json", "scoped_crawl_summary"),
            requires_human_approval=True,
            default_arguments={"max_minutes": 1},
        ),
    )
    return WSTGStrategyMap(entries)
