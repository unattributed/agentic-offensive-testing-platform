MODULE = {
    "name": "wstg_webapp",
    "supports": ("authentication", "session", "authorization", "input_validation", "security_headers", "client_side", "business_logic"),
    "requires": ("explicit_target_scope", "approved_case", "rate_limits"),
    "denies": ("target_expansion", "credential_guessing", "destructive_actions"),
}
