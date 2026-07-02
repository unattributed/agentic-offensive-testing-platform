"""Local-only OWASP Juice Shop benchmark target profile.

Juice Shop is an intentionally vulnerable benchmark target for validating AOTP
campaign behavior. This module is metadata-only. It must not contain challenge
solutions, target-specific exploit shortcuts, or special execution behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from aotp.wstg import WSTGAdapterFamily, WSTGEngineProfile, WSTGSafetyTier

JUICE_SHOP_IMAGE = "bkimminich/juice-shop"
JUICE_SHOP_CONTAINER_NAME = "aotp-juice-shop"
JUICE_SHOP_HOST = "127.0.0.1"
JUICE_SHOP_PORT = 3000
JUICE_SHOP_BASE_URL = f"http://{JUICE_SHOP_HOST}:{JUICE_SHOP_PORT}/"
JUICE_SHOP_AUTHORIZATION_REFERENCE = "local-loopback-intentionally-vulnerable-benchmark"


class JuiceShopProfileError(ValueError):
    """Raised when the local Juice Shop profile is unsafe or malformed."""


@dataclass(frozen=True)
class JuiceShopLocalProfile:
    """Metadata describing the local Juice Shop benchmark target."""

    target_alias: str = "local-juice-shop"
    base_url: str = JUICE_SHOP_BASE_URL
    image: str = JUICE_SHOP_IMAGE
    container_name: str = JUICE_SHOP_CONTAINER_NAME
    host: str = JUICE_SHOP_HOST
    port: int = JUICE_SHOP_PORT
    purpose: str = "aotp-wstg-campaign-benchmark"
    network_exposure: str = "loopback-only"
    reset_required_before_campaign: bool = True
    persistent_storage_allowed: bool = False

    def __post_init__(self) -> None:
        parsed = urlsplit(self.base_url)
        if parsed.scheme != "http":
            raise JuiceShopProfileError("local Juice Shop must use http on loopback")
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise JuiceShopProfileError("local Juice Shop must be bound to loopback only")
        if parsed.port != self.port:
            raise JuiceShopProfileError("base_url port must match the declared local port")
        if self.host != "127.0.0.1":
            raise JuiceShopProfileError("Docker host binding must be 127.0.0.1")
        if self.port < 1024 or self.port > 65535:
            raise JuiceShopProfileError("local Juice Shop port must be a non-privileged TCP port")
        if self.image != JUICE_SHOP_IMAGE:
            raise JuiceShopProfileError("benchmark must use the official Juice Shop image name")
        if self.container_name != JUICE_SHOP_CONTAINER_NAME:
            raise JuiceShopProfileError("container name must be stable for deterministic reset")
        if self.network_exposure != "loopback-only":
            raise JuiceShopProfileError("network exposure must remain loopback-only")
        if not self.reset_required_before_campaign:
            raise JuiceShopProfileError("a fresh reset is required before every campaign")
        if self.persistent_storage_allowed:
            raise JuiceShopProfileError("persistent storage would preserve old challenge state")

    @property
    def docker_port_binding(self) -> str:
        """Return the only allowed host-to-container port binding."""

        return f"{self.host}:{self.port}:3000"

    def docker_labels(self) -> dict[str, str]:
        """Return labels used by the install/reset scripts for inventory."""

        return {
            "aotp.purpose": self.purpose,
            "aotp.target": self.target_alias,
            "aotp.network_exposure": self.network_exposure,
            "aotp.reset_required": "true",
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_alias": self.target_alias,
            "base_url": self.base_url,
            "image": self.image,
            "container_name": self.container_name,
            "host": self.host,
            "port": self.port,
            "docker_port_binding": self.docker_port_binding,
            "purpose": self.purpose,
            "network_exposure": self.network_exposure,
            "reset_required_before_campaign": self.reset_required_before_campaign,
            "persistent_storage_allowed": self.persistent_storage_allowed,
            "docker_labels": self.docker_labels(),
        }


def local_juice_shop_profile() -> JuiceShopLocalProfile:
    """Return the default local-only Juice Shop benchmark profile."""

    return JuiceShopLocalProfile()


def build_local_juice_shop_wstg_profile(
    *,
    campaign_id: str = "local-juice-shop-wstg",
    max_ready_tests: int | None = 20,
) -> WSTGEngineProfile:
    """Build a governed WSTG profile for the local Juice Shop benchmark.

    The profile enables passive and safe-active work against the loopback-only
    benchmark. It does not approve intrusive or destructive testing.
    """

    profile = local_juice_shop_profile()
    return WSTGEngineProfile(
        campaign_id=campaign_id,
        target_alias=profile.target_alias,
        base_url=profile.base_url,
        authorization_reference=JUICE_SHOP_AUTHORIZATION_REFERENCE,
        operator_approved=True,
        allowed_safety_tiers=frozenset({WSTGSafetyTier.PASSIVE, WSTGSafetyTier.SAFE_ACTIVE}),
        allowed_adapter_families=frozenset(
            {
                WSTGAdapterFamily.HTTP,
                WSTGAdapterFamily.BROWSER,
                WSTGAdapterFamily.PROXY,
                WSTGAdapterFamily.TLS,
                WSTGAdapterFamily.API,
                WSTGAdapterFamily.MANUAL,
                WSTGAdapterFamily.MULTI_STEP,
            }
        ),
        authenticated=False,
        multi_role=False,
        privileged=False,
        source_assisted=False,
        allow_intrusive_active=False,
        max_ready_tests=max_ready_tests,
    )
