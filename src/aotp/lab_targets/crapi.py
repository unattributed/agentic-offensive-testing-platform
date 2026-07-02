"""Local-only OWASP crAPI benchmark target profile.

crAPI is an intentionally vulnerable API benchmark target for validating AOTP
campaign behavior beyond a browser-heavy web application. This module is
metadata-only. It must not contain challenge solutions, target-specific exploit
shortcuts, or special engine behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from aotp.wstg import WSTGAdapterFamily, WSTGEngineProfile, WSTGSafetyTier

CRAPI_TARGET_ALIAS = "local-crapi"
CRAPI_PROJECT_NAME = "aotp-crapi"
CRAPI_HOST = "127.0.0.1"
CRAPI_WEB_PORT = 8888
CRAPI_MAILHOG_PORT = 8025
CRAPI_BASE_URL = f"http://{CRAPI_HOST}:{CRAPI_WEB_PORT}/"
CRAPI_MAILHOG_URL = f"http://{CRAPI_HOST}:{CRAPI_MAILHOG_PORT}/"
CRAPI_SOURCE_ARCHIVE_URL = "https://github.com/OWASP/crAPI/archive/refs/heads/main.zip"
CRAPI_DOCKER_DIR = "crAPI-main/deploy/docker"
CRAPI_AUTHORIZATION_REFERENCE = "local-loopback-intentionally-vulnerable-api-benchmark"


class CapiProfileError(ValueError):
    """Raised when the local crAPI profile is unsafe or malformed."""


@dataclass(frozen=True)
class CapiLocalProfile:
    """Metadata describing the local crAPI benchmark target."""

    target_alias: str = CRAPI_TARGET_ALIAS
    base_url: str = CRAPI_BASE_URL
    mailhog_url: str = CRAPI_MAILHOG_URL
    project_name: str = CRAPI_PROJECT_NAME
    host: str = CRAPI_HOST
    web_port: int = CRAPI_WEB_PORT
    mailhog_port: int = CRAPI_MAILHOG_PORT
    source_archive_url: str = CRAPI_SOURCE_ARCHIVE_URL
    docker_dir: str = CRAPI_DOCKER_DIR
    purpose: str = "aotp-api-wstg-campaign-benchmark"
    network_exposure: str = "loopback-only"
    reset_required_before_campaign: bool = True
    persistent_storage_allowed: bool = False
    compose_required: bool = True
    live_runtime_status: str = "pending_unsupported"

    def __post_init__(self) -> None:
        self._validate_url(self.base_url, self.web_port, "base_url")
        self._validate_url(self.mailhog_url, self.mailhog_port, "mailhog_url")
        if self.host != "127.0.0.1":
            raise CapiProfileError("crAPI host binding must be 127.0.0.1")
        if self.target_alias != CRAPI_TARGET_ALIAS:
            raise CapiProfileError("crAPI target alias must remain local-crapi")
        if self.project_name != CRAPI_PROJECT_NAME:
            raise CapiProfileError("crAPI compose project name must remain deterministic")
        if self.network_exposure != "loopback-only":
            raise CapiProfileError("crAPI network exposure must remain loopback-only")
        if not self.reset_required_before_campaign:
            raise CapiProfileError("a fresh crAPI reset is required before every campaign")
        if self.persistent_storage_allowed:
            raise CapiProfileError("persistent crAPI storage would preserve old benchmark state")
        if not self.compose_required:
            raise CapiProfileError("crAPI is a compose-managed multi-container target")
        if self.source_archive_url != CRAPI_SOURCE_ARCHIVE_URL:
            raise CapiProfileError("crAPI source archive URL must be the official OWASP main archive")
        if self.docker_dir != CRAPI_DOCKER_DIR:
            raise CapiProfileError("crAPI docker directory must match the official archive layout")
        if self.live_runtime_status != "pending_unsupported":
            raise CapiProfileError("crAPI live runtime must remain pending until deterministic startup is proven")

    @staticmethod
    def _validate_url(url: str, port: int, field_name: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "http":
            raise CapiProfileError(f"{field_name} must use http on loopback")
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise CapiProfileError(f"{field_name} must be bound to loopback only")
        if parsed.port != port:
            raise CapiProfileError(f"{field_name} port must match the declared port")
        if port < 1024 or port > 65535:
            raise CapiProfileError("crAPI ports must be non-privileged TCP ports")

    @property
    def loopback_ports(self) -> tuple[str, ...]:
        """Return expected loopback listeners exposed by the official compose stack."""

        return (
            f"{self.host}:{self.web_port}",
            f"{self.host}:30080",
            f"{self.host}:8443",
            f"{self.host}:30443",
            f"{self.host}:{self.mailhog_port}",
        )

    @property
    def compose_environment(self) -> dict[str, str]:
        """Return the strict environment used by reset scripts."""

        return {
            "COMPOSE_PROJECT_NAME": self.project_name,
            "LISTEN_IP": self.host,
            "VERSION": "latest",
            "AOTP_TARGET_ALIAS": self.target_alias,
        }

    def labels(self) -> dict[str, str]:
        """Return AOTP labels used for inventory where compose supports them."""

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
            "mailhog_url": self.mailhog_url,
            "project_name": self.project_name,
            "host": self.host,
            "web_port": self.web_port,
            "mailhog_port": self.mailhog_port,
            "source_archive_url": self.source_archive_url,
            "docker_dir": self.docker_dir,
            "purpose": self.purpose,
            "network_exposure": self.network_exposure,
            "reset_required_before_campaign": self.reset_required_before_campaign,
            "persistent_storage_allowed": self.persistent_storage_allowed,
            "compose_required": self.compose_required,
            "live_runtime_status": self.live_runtime_status,
            "loopback_ports": list(self.loopback_ports),
            "compose_environment": dict(self.compose_environment),
            "labels": self.labels(),
        }


def local_crapi_profile() -> CapiLocalProfile:
    """Return the default local-only crAPI benchmark profile."""

    return CapiLocalProfile()


def build_local_crapi_wstg_profile(
    *,
    campaign_id: str = "local-crapi-wstg",
    max_ready_tests: int | None = 30,
) -> WSTGEngineProfile:
    """Build a governed WSTG profile for the local crAPI benchmark.

    This profile emphasizes API, authorization, authentication, information
    gathering, and business-logic planning while still respecting the generic
    WSTG engine's passive and safe-active bounds.
    """

    profile = local_crapi_profile()
    return WSTGEngineProfile(
        campaign_id=campaign_id,
        target_alias=profile.target_alias,
        base_url=profile.base_url,
        authorization_reference=CRAPI_AUTHORIZATION_REFERENCE,
        operator_approved=True,
        allowed_safety_tiers=frozenset({WSTGSafetyTier.PASSIVE, WSTGSafetyTier.SAFE_ACTIVE}),
        allowed_adapter_families=frozenset(
            {
                WSTGAdapterFamily.HTTP,
                WSTGAdapterFamily.API,
                WSTGAdapterFamily.BROWSER,
                WSTGAdapterFamily.PROXY,
                WSTGAdapterFamily.MANUAL,
                WSTGAdapterFamily.MULTI_STEP,
            }
        ),
        allowed_categories=frozenset({"INFO", "CONF", "ATHN", "ATHZ", "SESS", "BUSL", "APIT"}),
        authenticated=False,
        multi_role=False,
        privileged=False,
        source_assisted=False,
        allow_intrusive_active=False,
        max_ready_tests=max_ready_tests,
    )
