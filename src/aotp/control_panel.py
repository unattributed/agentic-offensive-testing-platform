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


def collect_panel_actions(objective: dict[str, Any]) -> tuple[str, ...]:
    """Return normalized panel actions requested by an objective."""
    actions: list[str] = []
    for field in ("action", "panel_action"):
        value = objective.get(field)
        if isinstance(value, str) and value.strip():
            actions.append(value.strip())
    requested = objective.get("requested_actions")
    if isinstance(requested, list):
        for value in requested:
            if isinstance(value, str) and value.strip():
                actions.append(value.strip())
    return tuple(dict.fromkeys(actions))


def denied_panel_actions(objective: dict[str, Any]) -> tuple[str, ...]:
    """Return unsafe panel actions requested by an objective."""
    return tuple(
        action for action in collect_panel_actions(objective) if action in PANEL_UNSAFE_ACTIONS
    )
