"""Bounded HTTP metadata tools for authorized Sprint 14 campaigns."""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit


MAX_BODY_BYTES = 65_536
SAFE_HEADERS = {
    "cache-control",
    "content-length",
    "content-security-policy",
    "content-type",
    "date",
    "location",
    "permissions-policy",
    "referrer-policy",
    "server",
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
}


class NativeToolError(RuntimeError):
    """Raised when a bounded native tool cannot complete safely."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class ToolExecutionResult:
    tool_name: str
    request_count: int
    result: dict[str, Any]


def _validate_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise NativeToolError(
            "HTTP metadata URL must be credential-free HTTP or HTTPS without query or fragment"
        )
    return value


def _open_default(request: urllib.request.Request, timeout: float):
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)


def _fetch(
    url: str,
    *,
    timeout_seconds: float,
    opener: Callable[[urllib.request.Request, float], Any],
) -> dict[str, Any]:
    request = urllib.request.Request(
        _validate_url(url),
        method="GET",
        headers={
            "Accept": "text/plain,text/html,application/json;q=0.8,*/*;q=0.1",
            "User-Agent": "AOTP-Sprint14-Metadata/1.0",
        },
    )
    try:
        try:
            response_context = opener(request, timeout_seconds)
        except urllib.error.HTTPError as exc:
            response_context = exc
        with response_context as response:
            body = response.read(MAX_BODY_BYTES + 1)
            if len(body) > MAX_BODY_BYTES:
                body = body[:MAX_BODY_BYTES]
                truncated = True
            else:
                truncated = False
            headers = {
                key.lower(): value
                for key, value in response.headers.items()
                if key.lower() in SAFE_HEADERS
            }
            return {
                "url": url,
                "status": int(response.status),
                "headers": headers,
                "body_bytes_observed": len(body),
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_truncated": truncated,
            }
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        raise NativeToolError("bounded HTTP metadata request failed") from exc


def fetch_http_metadata(
    url: str,
    *,
    timeout_seconds: float = 10,
    opener: Callable[[urllib.request.Request, float], Any] = _open_default,
) -> ToolExecutionResult:
    return ToolExecutionResult(
        tool_name="http_metadata",
        request_count=1,
        result=_fetch(url, timeout_seconds=timeout_seconds, opener=opener),
    )


def fetch_well_known_metadata(
    base_url: str,
    *,
    timeout_seconds: float = 10,
    opener: Callable[[urllib.request.Request, float], Any] = _open_default,
) -> ToolExecutionResult:
    origin = _validate_url(base_url).rstrip("/") + "/"
    results = []
    for path in ("robots.txt", ".well-known/security.txt"):
        results.append(
            _fetch(
                urljoin(origin, path),
                timeout_seconds=timeout_seconds,
                opener=opener,
            )
        )
    return ToolExecutionResult(
        tool_name="well_known_text",
        request_count=2,
        result={"checks": results},
    )
