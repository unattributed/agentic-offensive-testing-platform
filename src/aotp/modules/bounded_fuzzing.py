MODULE = {
    "name": "bounded_fuzzing",
    "supports": ("endpoint", "parameter", "form", "api", "file_input"),
    "requires": ("explicit_fuzzing_authorization", "payload_budget", "request_budget", "rate_limits"),
    "denies": ("high_volume", "destructive_payloads", "authentication_abuse", "payment_or_kyc"),
}
