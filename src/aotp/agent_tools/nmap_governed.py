"""Single-host, single-service governed nmap wrapper."""

from __future__ import annotations

import ipaddress
import re
import shutil
import subprocess
from pathlib import Path
from typing import Protocol

from .http_metadata import ToolExecutionResult


MAX_OUTPUT_BYTES = 65_536
HOSTNAME_PATTERN = re.compile(
    r"^(?=.{1,253}$)([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
)


class NmapGovernedError(RuntimeError):
    """Raised when governed nmap execution is unsafe or fails."""


class NmapRunner(Protocol):
    def __call__(
        self,
        argv: tuple[str, ...],
        *,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]: ...


def validate_single_host(host: str) -> str:
    if not isinstance(host, str) or not host:
        raise NmapGovernedError("nmap host is required")
    if any(character in host for character in ("/", "*", " ", "\t", "\n", "\r")):
        raise NmapGovernedError("nmap host must be a single host, not a range or pattern")
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    if HOSTNAME_PATTERN.fullmatch(host) is None:
        raise NmapGovernedError("nmap host must be a valid hostname or IP address")
    return host.lower().rstrip(".")


def validate_single_service_port(port: int) -> int:
    if not isinstance(port, int) or isinstance(port, bool) or port < 1 or port > 65535:
        raise NmapGovernedError("nmap port must be an integer from 1 to 65535")
    return port


def build_nmap_command(
    host: str,
    port: int,
    *,
    nmap_binary: str = "nmap",
    output_path: str | Path | None = None,
) -> tuple[str, ...]:
    safe_host = validate_single_host(host)
    safe_port = validate_single_service_port(port)
    argv = [
        nmap_binary,
        "-Pn",
        "-sV",
        "--version-light",
        "--max-retries",
        "1",
        "--host-timeout",
        "30s",
        "-p",
        str(safe_port),
    ]
    if output_path is not None:
        argv.extend(("-oX", str(output_path)))
    argv.extend(("--", safe_host))
    return tuple(argv)


def _default_runner(argv: tuple[str, ...], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )


def _truncate(value: str) -> str:
    encoded = value.encode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
    return encoded.decode("utf-8", errors="replace")


def run_governed_nmap(
    host: str,
    port: int,
    service_name: str,
    *,
    runner: NmapRunner = _default_runner,
    timeout_seconds: int = 45,
    nmap_binary: str | None = None,
    output_path: str | Path | None = None,
) -> ToolExecutionResult:
    """Run one bounded nmap command for one approved host and port."""

    if not isinstance(service_name, str) or not service_name or len(service_name) > 64:
        raise NmapGovernedError("service_name is required for provenance")
    if timeout_seconds < 1 or timeout_seconds > 120:
        raise NmapGovernedError("nmap timeout must be between 1 and 120 seconds")
    binary = nmap_binary or shutil.which("nmap")
    if binary is None:
        raise NmapGovernedError("nmap is not available")
    argv = build_nmap_command(host, port, nmap_binary=binary, output_path=output_path)
    try:
        completed = runner(argv, timeout=timeout_seconds)
    except (OSError, TimeoutError, subprocess.TimeoutExpired) as exc:
        raise NmapGovernedError("governed nmap command failed") from exc
    return ToolExecutionResult(
        tool_name="nmap_governed",
        request_count=1,
        result={
            "host": validate_single_host(host),
            "port": validate_single_service_port(port),
            "service_name": service_name,
            "argv": list(build_nmap_command(host, port, nmap_binary="nmap", output_path=output_path)),
            "returncode": int(completed.returncode),
            "stdout": _truncate(completed.stdout or ""),
            "stderr": _truncate(completed.stderr or ""),
            "output_truncated_at_bytes": MAX_OUTPUT_BYTES,
        },
    )
