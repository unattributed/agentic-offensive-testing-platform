"""Safe, evidence-only cryptographic controls review."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .redaction import assert_redacted, assert_value_redacted

CRYPTO_EVIDENCE_FILE = "crypto-evidence.json"
CRYPTO_SAFE_ACTIONS = frozenset({"inspect_provided_crypto_evidence"})
CRYPTO_UNSAFE_ACTIONS = frozenset(
    {"destructive_crypto_testing", "private_key_extraction", "secret_bruteforce"}
)


def build_crypto_record(case: dict[str, Any]) -> dict[str, Any]:
    tls = case.get("tls_evidence")
    cookies = case.get("cookie_attributes")
    token = case.get("token_configuration")
    indicators = case.get("weak_algorithm_indicators", [])
    key_management = case.get("key_management_metadata")
    if not isinstance(tls, dict):
        raise ValueError("TLS evidence is missing")
    if not isinstance(cookies, list):
        raise ValueError("cookie attribute evidence is missing")
    if not isinstance(token, dict):
        raise ValueError("token configuration evidence is missing")
    if not isinstance(indicators, list):
        raise ValueError("weak algorithm indicators are invalid")
    if not isinstance(key_management, dict):
        raise ValueError("key management metadata is missing")
    allowed_cookie_fields = {
        "cookie_alias",
        "secure",
        "http_only",
        "same_site",
        "host_only",
    }
    for cookie in cookies:
        if not isinstance(cookie, dict) or set(cookie) != allowed_cookie_fields:
            raise ValueError("cookie evidence must contain attributes only")
    forbidden_keys = {
        "cookie_value",
        "private_key",
        "secret",
        "token",
        "token_value",
        "value",
    }

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if set(value) & forbidden_keys:
                raise ValueError("cryptographic evidence contains forbidden secret fields")
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    payload = {
        "schema_version": "1.0",
        "record_type": "cryptographic_controls_evidence",
        "case_id": str(case.get("id", "")),
        "tls_evidence": tls,
        "cookie_attributes": cookies,
        "token_configuration": token,
        "weak_algorithm_indicators": indicators,
        "key_management_metadata": key_management,
        "network_silent": True,
        "request_count": 0,
        "private_material": "not_collected",
        "caveat": "Indicators are observations, not confirmed weaknesses, until evidence and human review establish impact.",
    }
    walk(payload)
    validate_crypto_record(payload)
    return payload


def validate_crypto_record(record: dict[str, Any]) -> None:
    if record.get("record_type") != "cryptographic_controls_evidence":
        raise ValueError("unsupported cryptographic evidence record")
    if record.get("network_silent") is not True or record.get("request_count") != 0:
        raise ValueError("cryptographic review must remain network silent")
    if record.get("private_material") != "not_collected":
        raise ValueError("private cryptographic material is forbidden")
    for indicator in record.get("weak_algorithm_indicators", []):
        if not isinstance(indicator, dict) or indicator.get("status") != "observation_only":
            raise ValueError("weak algorithm indicators must remain observations")
    encoded = json.dumps(record, sort_keys=True)
    assert_redacted(encoded)
    assert_value_redacted(record)


def write_crypto_record(record: dict[str, Any], directory: str | Path) -> Path:
    validate_crypto_record(record)
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    os.chmod(output, 0o700)
    path = output / CRYPTO_EVIDENCE_FILE
    descriptor, temporary_name = tempfile.mkstemp(prefix=".crypto-evidence.", dir=output)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return path
