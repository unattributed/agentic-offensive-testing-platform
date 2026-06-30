"""Canonical service control panel module contract."""

from ..control_panel import PANEL_SAFE_OBSERVATIONS, PANEL_UNSAFE_ACTIONS


MODULE = {
    "name": "service_control_panel",
    "supports": tuple(sorted(PANEL_SAFE_OBSERVATIONS)),
    "requires": ("explicit_panel_scope", "human_approval_for_state_change"),
    "denies": tuple(sorted(PANEL_UNSAFE_ACTIONS)),
}
