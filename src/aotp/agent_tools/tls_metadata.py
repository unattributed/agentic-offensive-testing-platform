"""Bounded TLS endpoint metadata for authorized Sprint 14 campaigns."""

from __future__ import annotations

import hashlib
import socket
import ssl
from typing import Any, Callable

from .http_metadata import NativeToolError, ToolExecutionResult


def _flatten_name(value: Any) -> dict[str, str]:
    flattened: dict[str, str] = {}
    if not isinstance(value, tuple):
        return flattened
    for group in value:
        if not isinstance(group, tuple):
            continue
        for item in group:
            if (
                isinstance(item, tuple)
                and len(item) == 2
                and all(isinstance(part, str) for part in item)
            ):
                flattened[item[0]] = item[1]
    return flattened


def fetch_tls_metadata(
    host: str,
    port: int,
    server_name: str,
    *,
    timeout_seconds: float = 10,
    connection_factory: Callable[..., Any] = socket.create_connection,
    context_factory: Callable[[], ssl.SSLContext] = ssl.create_default_context,
) -> ToolExecutionResult:
    if (
        not isinstance(host, str)
        or not host
        or not isinstance(server_name, str)
        or server_name != host
        or not isinstance(port, int)
        or isinstance(port, bool)
        or port <= 0
        or port > 65535
    ):
        raise NativeToolError("TLS metadata requires a valid host, matching SNI, and port")
    try:
        with connection_factory((host, port), timeout=timeout_seconds) as connection:
            with context_factory().wrap_socket(
                connection,
                server_hostname=server_name,
            ) as tls_socket:
                certificate = tls_socket.getpeercert()
                certificate_der = tls_socket.getpeercert(binary_form=True)
                cipher = tls_socket.cipher()
                sans = [
                    value
                    for kind, value in certificate.get("subjectAltName", ())
                    if kind == "DNS" and isinstance(value, str)
                ]
                result = {
                    "host": host,
                    "port": port,
                    "server_name": server_name,
                    "tls_version": tls_socket.version(),
                    "cipher": cipher[0] if cipher else None,
                    "certificate_sha256": hashlib.sha256(certificate_der).hexdigest(),
                    "subject": _flatten_name(certificate.get("subject")),
                    "issuer": _flatten_name(certificate.get("issuer")),
                    "not_before": certificate.get("notBefore"),
                    "not_after": certificate.get("notAfter"),
                    "subject_alt_names": sorted(sans),
                }
    except (OSError, TimeoutError, ssl.SSLError) as exc:
        raise NativeToolError("bounded TLS metadata connection failed") from exc
    return ToolExecutionResult(
        tool_name="tls_metadata",
        request_count=1,
        result=result,
    )
