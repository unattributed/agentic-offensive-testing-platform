MODULE = {
    "name": "crypto_controls",
    "supports": ("tls", "certificate_metadata", "cookie_attributes", "token_configuration", "weak_algorithm_indicators"),
    "requires": ("explicit_crypto_scope", "observable_or_provided_evidence"),
    "denies": ("private_key_extraction", "secret_bruteforce", "destructive_testing"),
}
