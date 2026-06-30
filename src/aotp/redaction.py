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
    "api_key",
    "authorization",
    "bearer",
    "cookie",
    "csrf",
    "password",
    "private_key",
    "secret",
    "session",
    "session_id",
    "token",
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
    return normalized in SENSITIVE_KEYS


def scan_value(value: Any, path: str = "$") -> list[RedactionFinding]:
    results: list[RedactionFinding] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if _sensitive_key(str(key)) and item not in (None, "", [], {}):
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
    findings = scan_value(value, path)
    if isinstance(value, str):
        return redact_text(value), findings
    if isinstance(value, list):
        cleaned = [sanitize_with_report(item, f"{path}[{index}]")[0] for index, item in enumerate(value)]
        return cleaned, findings
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if _sensitive_key(str(key)) and item not in (None, "", [], {}):
                cleaned[str(key)] = "[REDACTED:sensitive_field]"
            else:
                cleaned[str(key)] = sanitize_with_report(item, item_path)[0]
        return cleaned, findings
    return value, findings


def sanitize_for_model(value: Any) -> Any:
    return sanitize_with_report(value)[0]
