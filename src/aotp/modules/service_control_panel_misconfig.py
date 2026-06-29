MODULE = {
    "name": "service_control_panel",
    "supports": ("login_panel_observation", "security_headers", "tls_posture", "version_leakage", "default_pages", "metadata_exposure"),
    "requires": ("explicit_panel_scope", "human_approval_for_state_change"),
    "denies": ("credential_attacks", "lockout_behavior", "destructive_admin_actions"),
}
