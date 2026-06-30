"""Secret and private-data detection used at every output boundary."""

from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass
from typing import Any


PATTERNS: dict[str, re.Pattern[str]] = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "api_key": re.compile(r"(?i)\b(?:api[_-]?key|token)\s*[:=]\s*[A-Za-z0-9_./+\-]{12,}"),
    "bearer_token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    "cookie": re.compile(r"(?i)\b(?:cookie|set-cookie)\s*:\s*[^\r\n]+"),
    "session_id": re.compile(r"(?i)\b(?:session[_-]?id|sid)\s*[:=]\s*[A-Za-z0-9._~+/=-]{8,}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "email_address": re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b"),
    "basic_authorization": re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/=]{8,}"),
    "password": re.compile(r"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*\S{4,}"),
}

SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "bearer",
    "client_secret",
    "cookie",
    "cookie_value",
    "credential",
    "credentials",
    "csrf",
    "id_token",
    "password",
    "private_key",
    "private_key_material",
    "raw_cookie",
    "raw_token",
    "refresh_token",
    "secret",
    "secret_key",
    "session",
    "session_cookie",
    "session_id",
    "token",
    "token_value",
}


@dataclass(frozen=True)
class RedactionFinding:
    path: str
    kind: str
    value_sha256: str


def findings(text: str) -> list[str]:
    return sorted(name for name, pattern in PATTERNS.items() if pattern.search(text))


def assert_redacted(text: str) -> None:
    matches = findings(text)
    if matches:
        raise ValueError("redaction check failed: " + ", ".join(matches))


def redact_text(text: str) -> str:
    result = text
    for pattern in PATTERNS.values():
        result = pattern.sub("[REDACTED]", result)
    return result


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized.endswith(("_reference", "_alias", "_status", "_hash", "_sha256")):
        return False
    return normalized in SENSITIVE_KEYS or normalized.endswith(
        (
            "_access_token",
            "_client_secret",
            "_cookie_value",
            "_credential",
            "_password",
            "_private_key",
            "_private_key_material",
            "_raw_cookie",
            "_raw_token",
            "_refresh_token",
            "_secret",
            "_secret_key",
            "_session_cookie",
            "_token_value",
        )
    )


def _redacted_placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("[REDACTED") and value.endswith("]")


def scan_value(value: Any, path: str = "$") -> list[RedactionFinding]:
    results: list[RedactionFinding] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_matches = findings(key_text)
            item_path = (
                f"{path}.[redacted-key]" if key_matches else f"{path}.{key_text}"
            )
            for kind in key_matches:
                results.append(
                    RedactionFinding(
                        f"{path}.[redacted-key]",
                        kind,
                        hashlib.sha256(key_text.encode()).hexdigest(),
                    )
                )
            if (
                _sensitive_key(key_text)
                and item not in (None, "", [], {})
                and not _redacted_placeholder(item)
            ):
                encoded = str(item)
                results.append(
                    RedactionFinding(item_path, "sensitive_field", hashlib.sha256(encoded.encode()).hexdigest())
                )
            results.extend(scan_value(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            results.extend(scan_value(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(value):
                results.append(
                    RedactionFinding(
                        path,
                        kind,
                        hashlib.sha256(match.group(0).encode()).hexdigest(),
                    )
                )
    return sorted(set(results), key=lambda item: (item.path, item.kind, item.value_sha256))


def assert_value_redacted(value: Any) -> None:
    matches = scan_value(value)
    if matches:
        summary = ", ".join(f"{match.path}:{match.kind}" for match in matches)
        raise ValueError("redaction check failed: " + summary)


def sanitize_with_report(value: Any, path: str = "$") -> tuple[Any, list[RedactionFinding]]:
    report = scan_value(value, path)
    if isinstance(value, str):
        return redact_text(value), report
    if isinstance(value, list):
        cleaned = [sanitize_with_report(item, f"{path}[{index}]")[0] for index, item in enumerate(value)]
        return cleaned, report
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            key_text = str(key)
            key_matches = findings(key_text)
            cleaned_key = f"[REDACTED:key:{index}]" if key_matches else key_text
            item_path = (
                f"{path}.[redacted-key]" if key_matches else f"{path}.{key_text}"
            )
            if _sensitive_key(key_text) and item not in (None, "", [], {}):
                cleaned[cleaned_key] = "[REDACTED:sensitive_field]"
            else:
                cleaned[cleaned_key] = sanitize_with_report(item, item_path)[0]
        return cleaned, report
    return value, report


def sanitize_for_model(value: Any) -> Any:
    return sanitize_with_report(value)[0]
