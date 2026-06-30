"""Service control panel target model and safety boundary helpers."""
from __future__ import annotations

from typing import Any

PANEL_TYPES = frozenset(
    {
        "admin_panel",
        "service_console",
        "monitoring_panel",
        "mail_admin_interface",
        "ci_cd_panel",
        "cloud_console_placeholder",
        "generic_management_interface",
    }
)

PANEL_SAFE_OBSERVATIONS = frozenset(
    {
        "default_page_metadata",
        "indexing_metadata",
        "login_exposure_metadata",
        "response_header_metadata",
        "tls_configuration_metadata",
        "version_banner_metadata",
    }
)

PANEL_OBSERVATION_DESCRIPTIONS = {
    "default_page_metadata": "Record placeholder metadata about whether a default panel landing page is in scope.",
    "indexing_metadata": "Record placeholder metadata about indexing exposure without crawling the panel.",
    "login_exposure_metadata": "Record placeholder metadata about login surface exposure without submitting credentials.",
    "response_header_metadata": "Record placeholder metadata for response security headers without sending a request.",
    "tls_configuration_metadata": "Record placeholder metadata for TLS review without opening a network connection.",
    "version_banner_metadata": "Record placeholder metadata for visible version banners without exploitation claims.",
}

PANEL_UNSAFE_ACTIONS = frozenset(
    {
        "brute_force",
        "credential_attack",
        "credential_guessing",
        "credential_stuffing",
        "default_password_check",
        "destructive_action",
        "destructive_panel_action",
        "login_attempt",
        "lockout_triggering",
        "panel_crawl",
        "password_spraying",
        "session_hijacking",
        "token_replay",
        "unsafe_crawling",
    }
)


def _collect_text_values(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def collect_panel_actions(objective: dict[str, Any]) -> tuple[str, ...]:
    """Return normalized panel actions requested by an objective."""
    actions: list[str] = []
    for field in ("action", "panel_action", "requested_actions"):
        actions.extend(_collect_text_values(objective.get(field)))
    return tuple(dict.fromkeys(actions))


def collect_panel_observations(objective: dict[str, Any]) -> tuple[str, ...]:
    """Return normalized safe observation names requested by an objective."""
    observations: list[str] = []
    for field in ("panel_observation", "requested_observations"):
        observations.extend(_collect_text_values(objective.get(field)))
    return tuple(dict.fromkeys(observations))


def denied_panel_actions(objective: dict[str, Any]) -> tuple[str, ...]:
    """Return unsafe panel actions requested by an objective."""
    return tuple(
        action for action in collect_panel_actions(objective) if action in PANEL_UNSAFE_ACTIONS
    )


def unsafe_panel_observations(objective: dict[str, Any]) -> tuple[str, ...]:
    """Return requested observation names that are not approved as safe."""
    return tuple(
        observation
        for observation in collect_panel_observations(objective)
        if observation not in PANEL_SAFE_OBSERVATIONS
    )


def build_panel_dry_run_observation_plan(objective: dict[str, Any]) -> dict[str, Any]:
    """Build deterministic dry-run evidence metadata for safe panel observations.

    This function models work only. It does not open sockets, send HTTP requests,
    submit credentials, crawl panels, or create vulnerability findings.
    """
    requested = collect_panel_observations(objective) or tuple(sorted(PANEL_SAFE_OBSERVATIONS))
    planned = [
        {
            "observation_id": observation,
            "description": PANEL_OBSERVATION_DESCRIPTIONS.get(
                observation, "Unsupported observation was not executed."
            ),
            "execution": "not_executed",
            "evidence_placeholder": f"{observation}_placeholder",
            "safety_boundary": "metadata placeholder only; no login, crawl, mutation, or network request",
        }
        for observation in requested
    ]
    return {
        "panel_alias": str(objective.get("panel_alias", "")),
        "panel_type": str(objective.get("panel_type", "")),
        "target_alias": str(objective.get("target_alias", "")),
        "planned_observations": planned,
        "network_silent": True,
        "request_count": 0,
        "credential_material": "not_collected",
        "screenshots": [],
        "captures": [],
        "finding_claims": [],
        "denied_runtime_behaviors": sorted(PANEL_UNSAFE_ACTIONS),
    }
