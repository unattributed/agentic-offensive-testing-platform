"""Generic campaign target runtime contracts.

This module describes what a live campaign may touch. It is intentionally
metadata and policy heavy: target profiles can supply benchmark details, but the
WSTG execution harness does not depend on target-specific exploit logic.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from aotp.lab_targets.registry import get_local_target_entry
from aotp.wstg import WSTGAdapterFamily, WSTGEngineProfile, WSTGSafetyTier

BenchmarkComparator = Callable[[list[str]], dict[str, Any]]
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_ALLOWED_EXPOSURES = {"loopback-only", "authorized-external", "internal-sow"}
_DEFAULT_ALLOWED_METHODS = frozenset({"GET"})
_DEFAULT_ADAPTER_FAMILIES = frozenset(
    {
        WSTGAdapterFamily.HTTP,
        WSTGAdapterFamily.BROWSER,
        WSTGAdapterFamily.PROXY,
        WSTGAdapterFamily.TLS,
        WSTGAdapterFamily.API,
        WSTGAdapterFamily.MANUAL,
        WSTGAdapterFamily.MULTI_STEP,
    }
)
_DEFAULT_SAFETY_TIERS = frozenset({WSTGSafetyTier.PASSIVE, WSTGSafetyTier.SAFE_ACTIVE})


class TargetRuntimeError(ValueError):
    """Raised when a campaign target runtime is unsafe or unsupported."""


@dataclass(frozen=True)
class CampaignTargetRuntime:
    """Approved runtime boundary for one live WSTG campaign target."""

    target_alias: str
    base_url: str
    authorization_reference: str
    network_exposure: str
    implemented_live_target: bool
    reset_required_before_campaign: bool
    safe_paths: tuple[str, ...]
    allowed_methods: frozenset[str] = _DEFAULT_ALLOWED_METHODS
    allowed_safety_tiers: frozenset[WSTGSafetyTier] = _DEFAULT_SAFETY_TIERS
    allowed_adapter_families: frozenset[WSTGAdapterFamily] = _DEFAULT_ADAPTER_FAMILIES
    authenticated: bool = False
    multi_role: bool = False
    privileged: bool = False
    source_assisted: bool = False
    allow_intrusive_active: bool = False
    max_ready_tests: int | None = 30
    max_actions: int = 12
    benchmark_comparator: BenchmarkComparator | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if _SAFE_ID.fullmatch(self.target_alias) is None:
            raise TargetRuntimeError("target_alias must be a safe lowercase identifier")
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise TargetRuntimeError("base_url must be an absolute http or https URL")
        if parsed.username is not None or parsed.password is not None:
            raise TargetRuntimeError("base_url credentials are not allowed")
        if parsed.query or parsed.fragment:
            raise TargetRuntimeError("base_url query and fragment are not allowed")
        if self.network_exposure not in _ALLOWED_EXPOSURES:
            raise TargetRuntimeError("unsupported network exposure")
        if self.network_exposure == "loopback-only" and parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise TargetRuntimeError("loopback-only targets must use localhost or 127.0.0.1")
        if not self.implemented_live_target:
            raise TargetRuntimeError("target runtime is not implemented for live execution")
        if not self.reset_required_before_campaign:
            raise TargetRuntimeError("live target runtimes must require reset before campaign")
        if not self.authorization_reference.strip():
            raise TargetRuntimeError("authorization_reference is required")
        if not self.safe_paths:
            raise TargetRuntimeError("safe_paths are required for bounded execution")
        if any(method != method.upper() for method in self.allowed_methods):
            raise TargetRuntimeError("allowed methods must be uppercase")
        if "GET" not in self.allowed_methods:
            raise TargetRuntimeError("GET must remain available for passive discovery")
        if self.max_actions < 1 or self.max_actions > 100:
            raise TargetRuntimeError("max_actions must be between 1 and 100")
        if self.max_ready_tests is not None and (self.max_ready_tests < 1 or self.max_ready_tests > 97):
            raise TargetRuntimeError("max_ready_tests must be between 1 and the WSTG catalog size")
        for path in self.safe_paths:
            _validate_safe_path(path)

    @property
    def normalized_base_url(self) -> str:
        return self.base_url if self.base_url.endswith("/") else f"{self.base_url}/"

    @property
    def origin(self) -> str:
        parsed = urlsplit(self.base_url)
        default_port = 443 if parsed.scheme == "https" else 80
        suffix = f":{parsed.port}" if parsed.port and parsed.port != default_port else ""
        return f"{parsed.scheme}://{parsed.hostname}{suffix}"

    def build_wstg_profile(self, *, campaign_id: str | None = None, max_ready_tests: int | None = None) -> WSTGEngineProfile:
        """Build the generic WSTG engine profile for this runtime."""

        return WSTGEngineProfile(
            campaign_id=campaign_id or self.target_alias.replace("local-", "local-") + "-wstg-live",
            target_alias=self.target_alias,
            base_url=self.normalized_base_url,
            authorization_reference=self.authorization_reference,
            operator_approved=True,
            allowed_safety_tiers=self.allowed_safety_tiers,
            allowed_adapter_families=self.allowed_adapter_families,
            authenticated=self.authenticated,
            multi_role=self.multi_role,
            privileged=self.privileged,
            source_assisted=self.source_assisted,
            allow_intrusive_active=self.allow_intrusive_active,
            max_ready_tests=max_ready_tests if max_ready_tests is not None else self.max_ready_tests,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_alias": self.target_alias,
            "base_url": self.normalized_base_url,
            "authorization_reference": self.authorization_reference,
            "network_exposure": self.network_exposure,
            "implemented_live_target": self.implemented_live_target,
            "reset_required_before_campaign": self.reset_required_before_campaign,
            "safe_paths": list(self.safe_paths),
            "allowed_methods": sorted(self.allowed_methods),
            "allowed_safety_tiers": sorted(tier.value for tier in self.allowed_safety_tiers),
            "allowed_adapter_families": sorted(family.value for family in self.allowed_adapter_families),
            "authenticated": self.authenticated,
            "multi_role": self.multi_role,
            "privileged": self.privileged,
            "source_assisted": self.source_assisted,
            "allow_intrusive_active": self.allow_intrusive_active,
            "max_ready_tests": self.max_ready_tests,
            "max_actions": self.max_actions,
            "notes": list(self.notes),
        }


def build_juice_shop_target_runtime(
    *,
    safe_paths: tuple[str, ...] | None = None,
    max_ready_tests: int | None = 30,
    max_actions: int = 12,
) -> CampaignTargetRuntime:
    """Build the implemented local Juice Shop runtime without embedding challenge solutions."""

    from aotp.benchmarks.juice_shop import compare_wstg_observations
    from aotp.lab_targets.juice_shop import JUICE_SHOP_AUTHORIZATION_REFERENCE, local_juice_shop_profile

    profile = local_juice_shop_profile()
    return CampaignTargetRuntime(
        target_alias=profile.target_alias,
        base_url=profile.base_url,
        authorization_reference=JUICE_SHOP_AUTHORIZATION_REFERENCE,
        network_exposure=profile.network_exposure,
        implemented_live_target=True,
        reset_required_before_campaign=profile.reset_required_before_campaign,
        safe_paths=safe_paths
        or (
            "/",
            "/robots.txt",
            "/sitemap.xml",
            "/api/Products",
            "/rest/products/search?q=",
        ),
        max_ready_tests=max_ready_tests,
        max_actions=max_actions,
        benchmark_comparator=lambda observed: compare_wstg_observations(observed),
        notes=("generic harness runtime", "no Juice Shop challenge solutions"),
    )


def runtime_from_local_target_registry(target_alias: str) -> CampaignTargetRuntime:
    """Return a live runtime for implemented local targets and fail closed for planned targets."""

    entry = get_local_target_entry(target_alias)
    if not entry.implemented_live_target:
        raise TargetRuntimeError(f"local target is registered but not live-executable: {target_alias}")
    if entry.target_alias == "local-juice-shop":
        return build_juice_shop_target_runtime()
    raise TargetRuntimeError(f"no generic live runtime is implemented for: {target_alias}")


def _validate_safe_path(path: str) -> None:
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc:
        raise TargetRuntimeError("safe paths must be relative to the approved target origin")
    if not path.startswith("/"):
        raise TargetRuntimeError("safe paths must start with /")
    if ".." in parsed.path.split("/"):
        raise TargetRuntimeError("path traversal segments are not allowed in safe paths")
