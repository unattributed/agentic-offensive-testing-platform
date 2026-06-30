"""Canonical cryptographic controls module contract."""

from ..crypto_review import CRYPTO_UNSAFE_ACTIONS


MODULE = {
    "name": "crypto_controls",
    "supports": ("tls", "certificate_metadata", "cookie_attributes", "token_configuration", "weak_algorithm_indicators"),
    "requires": ("explicit_crypto_scope", "observable_or_provided_evidence"),
    "denies": tuple(sorted(CRYPTO_UNSAFE_ACTIONS)),
}
