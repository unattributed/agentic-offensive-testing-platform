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
    {
        "decryption_attempt",
        "destructive_crypto_testing",
        "key_extraction",
        "live_crypto_probe",
        "live_tls_probe",
        "private_key_extraction",
        "secret_bruteforce",
        "token_replay",
    }
)

TLS_FIELDS = {
    "protocol",
    "certificate_subject_alias",
    "certificate_issuer_alias",
    "public_key_algorithm",
    "public_key_bits",
    "signature_algorithm",
}
COOKIE_FIELDS = {"cookie_alias", "secure", "http_only", "same_site", "host_only"}
TOKEN_FIELDS = {
    "algorithm",
    "issuer_validation",
    "audience_validation",
    "expiration_validation",
    "key_source_alias",
}
KEY_MANAGEMENT_FIELDS = {
    "provider_alias",
    "storage_type",
    "rotation_configured",
    "private_material_present",
}
FORBIDDEN_KEYS = {
    "cookie_value",
    "key_material",
    "private_key",
    "private_key_material",
    "private_material",
    "raw_cookie",
    "raw_token",
    "secret",
    "token",
    "token_value",
    "value",
}


def crypto_action_is_unsafe(action: Any) -> bool:
    if not isinstance(action, str):
        return False
    normalized = action.strip().lower().replace("-", "_")
    if normalized in CRYPTO_UNSAFE_ACTIONS:
        return True
    return any(
        marker in normalized
        for marker in (
            "brute_force",
            "bruteforce",
            "decrypt",
            "destructive",
            "extract",
            "live_probe",
            "live_tls",
            "probe_live",
            "replay",
        )
    )


def crypto_evidence_errors(case: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    tls = case.get("tls_evidence")
    cookies = case.get("cookie_attributes")
    token = case.get("token_configuration")
    indicators = case.get("weak_algorithm_indicators", [])
    key_management = case.get("key_management_metadata")
    if not isinstance(tls, dict) or set(tls) != TLS_FIELDS:
        errors.append("TLS evidence is missing or contains unsupported fields")
    if not isinstance(cookies, list):
        errors.append("cookie attribute evidence is missing")
        cookies = []
    if not isinstance(token, dict) or set(token) != TOKEN_FIELDS:
        errors.append("token configuration evidence is missing or contains unsupported fields")
    if not isinstance(indicators, list):
        errors.append("weak algorithm indicators are invalid")
        indicators = []
    if not isinstance(key_management, dict) or set(key_management) != KEY_MANAGEMENT_FIELDS:
        errors.append("key management metadata is missing or contains unsupported fields")
    elif key_management.get("private_material_present") is not False:
        errors.append("private key material is forbidden")
    for cookie in cookies:
        if not isinstance(cookie, dict) or set(cookie) != COOKIE_FIELDS:
            errors.append("cookie evidence must contain attributes only")

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if set(value) & FORBIDDEN_KEYS:
                errors.append("cryptographic evidence contains forbidden secret fields")
            for key, item in value.items():
                if str(key).endswith("_path") or key in {"artifact", "path"}:
                    if not isinstance(item, str):
                        errors.append("cryptographic evidence path must be text")
                    else:
                        path = Path(item)
                        if path.is_absolute() or ".." in path.parts:
                            errors.append("cryptographic evidence path must remain relative")
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(case)
    try:
        assert_redacted(json.dumps(case, sort_keys=True))
        assert_value_redacted(case)
    except ValueError as exc:
        errors.append(str(exc))
    return tuple(dict.fromkeys(errors))


def build_crypto_record(case: dict[str, Any]) -> dict[str, Any]:
    errors = crypto_evidence_errors(case)
    if errors:
        raise ValueError("; ".join(errors))
    tls = case["tls_evidence"]
    cookies = case["cookie_attributes"]
    token = case["token_configuration"]
    indicators = case.get("weak_algorithm_indicators", [])
    key_management = case["key_management_metadata"]

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
