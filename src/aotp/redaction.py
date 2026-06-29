"""Secret and private-data detection used at every output boundary."""

from __future__ import annotations

import re
from typing import Any


PATTERNS: dict[str, re.Pattern[str]] = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "api_key": re.compile(r"(?i)\b(?:api[_-]?key|token)\s*[:=]\s*[A-Za-z0-9_./+\-]{12,}"),
    "bearer_token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    "cookie": re.compile(r"(?i)\b(?:cookie|set-cookie)\s*:\s*[^\r\n]+"),
    "session_id": re.compile(r"(?i)\b(?:session[_-]?id|sid)\s*[:=]\s*[A-Za-z0-9._~+/=-]{8,}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "email_address": re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE),
}


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


def sanitize_for_model(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [sanitize_for_model(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_for_model(item) for key, item in value.items()}
    return value
