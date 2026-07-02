"""Generic AOTP WSTG planning engine.

The engine plans against the complete canonical OWASP WSTG v4.2 catalog. It must not depend on any target-specific integration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urlsplit

from .catalog import (
    WSTGAdapterFamily,
    WSTGAuthRequirement,
    WSTGCatalog,
    WSTGSafetyTier,
    WSTGTestCase,
    WSTG_V42_CATALOG,
)


class WSTGEngineError(ValueError):
    """Raised when a generic WSTG campaign plan is unsafe or invalid."""


class WSTGPlanDisposition(str, Enum):
    """Disposition assigned to each canonical WSTG test during planning."""

    READY = "ready"
    DEFERRED = "deferred"
    DENIED = "denied"


@dataclass(frozen=True)
class WSTGEngineProfile:
    """Authorized target and execution bounds for a WSTG campaign plan."""

    campaign_id: str
    target_alias: str
    base_url: str
    authorization_reference: str
    operator_approved: bool
    allowed_safety_tiers: frozenset[WSTGSafetyTier]
    allowed_adapter_families: frozenset[WSTGAdapterFamily]
    allowed_categories: frozenset[str] | None = None
    authenticated: bool = False
    multi_role: bool = False
    privileged: bool = False
    source_assisted: bool = False
    allow_intrusive_active: bool = False
    max_ready_tests: int | None = None

    def __post_init__(self) -> None:
        for name, value in (("campaign_id", self.campaign_id), ("target_alias", self.target_alias)):
            if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", value) is None:
                raise WSTGEngineError(f"{name} must be a safe lowercase identifier")
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise WSTGEngineError("base_url must be an absolute http or https URL")
        if parsed.username is not None or parsed.password is not None:
            raise WSTGEngineError("base_url credentials are not allowed")
        if parsed.query or parsed.fragment:
            raise WSTGEngineError("base_url query and fragment are not allowed")
        if not self.authorization_reference.strip():
            raise WSTGEngineError("authorization_reference is required")
        if not self.operator_approved:
            raise WSTGEngineError("operator approval is required")
        if not self.allowed_safety_tiers:
            raise WSTGEngineError("at least one safety tier must be allowed")
        if not self.allowed_adapter_families:
            raise WSTGEngineError("at least one adapter family must be allowed")
        if self.max_ready_tests is not None and self.max_ready_tests < 1:
            raise WSTGEngineError("max_ready_tests must be positive when provided")

    @property
    def origin(self) -> str:
        parsed = urlsplit(self.base_url)
        default_port = 443 if parsed.scheme == "https" else 80
        suffix = f":{parsed.port}" if parsed.port and parsed.port != default_port else ""
        return f"{parsed.scheme}://{parsed.hostname}{suffix}"


@dataclass(frozen=True)
class WSTGPlannedTest:
    """Plan record for one canonical WSTG test case."""

    objective_id: str
    test_case: WSTGTestCase
    disposition: WSTGPlanDisposition
    reasons: tuple[str, ...]
    arguments: dict[str, Any]

    @property
    def wstg_id(self) -> str:
        return self.test_case.wstg_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "wstg_id": self.wstg_id,
            "title": self.test_case.title,
            "category": self.test_case.category,
            "category_name": self.test_case.category_name,
            "disposition": self.disposition.value,
            "reasons": list(self.reasons),
            "adapter_family": self.test_case.adapter_family.value,
            "safety_tier": self.test_case.safety_tier.value,
            "auth_requirement": self.test_case.auth_requirement.value,
            "evidence_required": list(self.test_case.evidence_required),
            "arguments": dict(self.arguments),
        }


@dataclass(frozen=True)
class WSTGEnginePlan:
    """Complete WSTG matrix for a target, including ready and deferred tests."""

    campaign_id: str
    target_alias: str
    base_url: str
    authorization_reference: str
    catalog_version: str
    planned_tests: tuple[WSTGPlannedTest, ...]

    @property
    def ready_tests(self) -> tuple[WSTGPlannedTest, ...]:
        return tuple(test for test in self.planned_tests if test.disposition is WSTGPlanDisposition.READY)

    @property
    def deferred_tests(self) -> tuple[WSTGPlannedTest, ...]:
        return tuple(test for test in self.planned_tests if test.disposition is WSTGPlanDisposition.DEFERRED)

    @property
    def denied_tests(self) -> tuple[WSTGPlannedTest, ...]:
        return tuple(test for test in self.planned_tests if test.disposition is WSTGPlanDisposition.DENIED)

    def coverage_summary(self) -> dict[str, Any]:
        statuses = {disposition.value: 0 for disposition in WSTGPlanDisposition}
        categories: dict[str, dict[str, int]] = {}
        for test in self.planned_tests:
            statuses[test.disposition.value] += 1
            categories.setdefault(test.test_case.category, {disposition.value: 0 for disposition in WSTGPlanDisposition})
            categories[test.test_case.category][test.disposition.value] += 1
        return {
            "total": len(self.planned_tests),
            "statuses": statuses,
            "categories": categories,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "target_alias": self.target_alias,
            "base_url": self.base_url,
            "authorization_reference": self.authorization_reference,
            "catalog_version": self.catalog_version,
            "coverage_summary": self.coverage_summary(),
            "planned_tests": [test.as_dict() for test in self.planned_tests],
        }


def _auth_reasons(profile: WSTGEngineProfile, test_case: WSTGTestCase) -> tuple[str, ...]:
    requirement = test_case.auth_requirement
    if requirement is WSTGAuthRequirement.ANONYMOUS:
        return ()
    if requirement is WSTGAuthRequirement.AUTHENTICATED and not profile.authenticated:
        return ("authenticated context required",)
    if requirement is WSTGAuthRequirement.MULTI_ROLE and not profile.multi_role:
        return ("multi-role authorization context required",)
    if requirement is WSTGAuthRequirement.PRIVILEGED and not profile.privileged:
        return ("privileged authorization context required",)
    if requirement is WSTGAuthRequirement.SOURCE_ASSISTED and not profile.source_assisted:
        return ("source-assisted context required",)
    return ()


def _planning_reasons(profile: WSTGEngineProfile, test_case: WSTGTestCase) -> tuple[str, ...]:
    reasons: list[str] = []
    if profile.allowed_categories is not None and test_case.category not in profile.allowed_categories:
        reasons.append("category not selected for this campaign")
    if test_case.adapter_family not in profile.allowed_adapter_families:
        reasons.append("adapter family not approved for this campaign")
    if test_case.safety_tier not in profile.allowed_safety_tiers:
        reasons.append("safety tier not approved for this campaign")
    if test_case.safety_tier is WSTGSafetyTier.INTRUSIVE_ACTIVE and not profile.allow_intrusive_active:
        reasons.append("intrusive active testing requires explicit campaign approval")
    reasons.extend(_auth_reasons(profile, test_case))
    return tuple(reasons)


def build_wstg_engine_plan(
    profile: WSTGEngineProfile,
    *,
    catalog: WSTGCatalog = WSTG_V42_CATALOG,
) -> WSTGEnginePlan:
    """Build a complete governed WSTG campaign matrix for an authorized target."""

    planned: list[WSTGPlannedTest] = []
    ready_count = 0
    for test_case in catalog.cases():
        reasons = list(_planning_reasons(profile, test_case))
        disposition = WSTGPlanDisposition.READY
        if reasons:
            disposition = WSTGPlanDisposition.DEFERRED
        elif profile.max_ready_tests is not None and ready_count >= profile.max_ready_tests:
            disposition = WSTGPlanDisposition.DEFERRED
            reasons.append("ready test limit reached for this campaign slice")
        else:
            ready_count += 1
        if test_case.safety_tier is WSTGSafetyTier.DESTRUCTIVE_DENIED:
            disposition = WSTGPlanDisposition.DENIED
            reasons.append("destructive testing is denied by policy")
        planned.append(
            WSTGPlannedTest(
                objective_id=f"{profile.campaign_id}:{test_case.wstg_id}",
                test_case=test_case,
                disposition=disposition,
                reasons=tuple(reasons),
                arguments={
                    "base_url": profile.base_url,
                    "origin": profile.origin,
                    "target_alias": profile.target_alias,
                    "authorization_reference": profile.authorization_reference,
                    "wstg_id": test_case.wstg_id,
                    "source_url": test_case.source_url,
                },
            )
        )
    return WSTGEnginePlan(
        campaign_id=profile.campaign_id,
        target_alias=profile.target_alias,
        base_url=profile.base_url,
        authorization_reference=profile.authorization_reference,
        catalog_version="v42",
        planned_tests=tuple(planned),
    )
