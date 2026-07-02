"""Registry for local vulnerable benchmark targets.

The registry is metadata-only. It lets AOTP enumerate and validate local lab
targets without making any target a dependency of the core WSTG engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .crapi import build_local_crapi_wstg_profile, local_crapi_profile
from .juice_shop import build_local_juice_shop_wstg_profile, local_juice_shop_profile

ProfileBuilder = Callable[[], Any]
WSTGProfileBuilder = Callable[..., Any]


@dataclass(frozen=True)
class LocalTargetRegistryEntry:
    """Metadata for one local benchmark target family."""

    target_alias: str
    display_name: str
    category: str
    lifecycle: str
    base_url: str
    reset_required_before_campaign: bool
    network_exposure: str
    implemented_live_target: bool
    benchmark_manifest: str | None
    profile_builder: ProfileBuilder
    wstg_profile_builder: WSTGProfileBuilder
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.network_exposure != "loopback-only":
            raise ValueError(f"{self.target_alias} must remain loopback-only")
        if not self.reset_required_before_campaign:
            raise ValueError(f"{self.target_alias} must require reset before campaign")
        if not self.target_alias.startswith("local-"):
            raise ValueError("local benchmark target aliases must start with local-")
        if self.lifecycle not in {"implemented", "planned"}:
            raise ValueError("lifecycle must be implemented or planned")
        if self.implemented_live_target and self.benchmark_manifest is None:
            raise ValueError("implemented targets need a benchmark manifest reference")

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_alias": self.target_alias,
            "display_name": self.display_name,
            "category": self.category,
            "lifecycle": self.lifecycle,
            "base_url": self.base_url,
            "reset_required_before_campaign": self.reset_required_before_campaign,
            "network_exposure": self.network_exposure,
            "implemented_live_target": self.implemented_live_target,
            "benchmark_manifest": self.benchmark_manifest,
            "notes": list(self.notes),
        }


def build_local_target_registry() -> tuple[LocalTargetRegistryEntry, ...]:
    """Return the implemented local vulnerable target registry."""

    juice_shop = local_juice_shop_profile()
    crapi = local_crapi_profile()
    return (
        LocalTargetRegistryEntry(
            target_alias=juice_shop.target_alias,
            display_name="OWASP Juice Shop",
            category="modern-web-application",
            lifecycle="implemented",
            base_url=juice_shop.base_url,
            reset_required_before_campaign=juice_shop.reset_required_before_campaign,
            network_exposure=juice_shop.network_exposure,
            implemented_live_target=True,
            benchmark_manifest="aotp.benchmarks.juice_shop.build_juice_shop_benchmark_manifest",
            profile_builder=local_juice_shop_profile,
            wstg_profile_builder=build_local_juice_shop_wstg_profile,
            notes=("browser-heavy benchmark", "already supports bounded agentic campaign runner"),
        ),
        LocalTargetRegistryEntry(
            target_alias=crapi.target_alias,
            display_name="OWASP crAPI",
            category="modern-api-and-business-logic",
            lifecycle="planned",
            base_url=crapi.base_url,
            reset_required_before_campaign=crapi.reset_required_before_campaign,
            network_exposure=crapi.network_exposure,
            implemented_live_target=False,
            benchmark_manifest="aotp.benchmarks.crapi.build_crapi_benchmark_manifest",
            profile_builder=local_crapi_profile,
            wstg_profile_builder=build_local_crapi_wstg_profile,
            notes=("compose-managed benchmark", "registered WSTG benchmark mapping", "live runtime pending on Parrot rootless Podman Compose"),
        ),
    )


def get_local_target_entry(target_alias: str) -> LocalTargetRegistryEntry:
    """Return one local target registry entry by alias."""

    for entry in build_local_target_registry():
        if entry.target_alias == target_alias:
            return entry
    raise KeyError(f"unknown local target alias: {target_alias}")


def implemented_local_target_aliases() -> tuple[str, ...]:
    """Return aliases for targets that have live reset/install support."""

    return tuple(entry.target_alias for entry in build_local_target_registry() if entry.implemented_live_target)
