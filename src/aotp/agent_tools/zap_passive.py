"""Bounded OWASP ZAP passive baseline wrapper."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

from .http_metadata import ToolExecutionResult


MAX_OUTPUT_BYTES = 65_536


class ZapPassiveError(RuntimeError):
    """Raised when ZAP passive baseline execution is unsafe or fails."""


class ZapRunner(Protocol):
    def __call__(
        self,
        argv: tuple[str, ...],
        *,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]: ...


def validate_passive_target_url(target_url: str) -> str:
    parsed = urlsplit(target_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ZapPassiveError("ZAP passive target must be credential-free HTTP or HTTPS without query or fragment")
    return target_url.rstrip("/") + ("/" if parsed.path in {"", "/"} else "")


def _origin_tuple(url: str) -> tuple[str, str, int]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ZapPassiveError("ZAP passive URL has no comparable origin")
    default_port = 443 if parsed.scheme == "https" else 80
    return parsed.scheme, parsed.hostname.lower().rstrip("."), parsed.port or default_port


def validate_zap_output_scope(target_url: str, *output_chunks: str) -> None:
    """Reject evidence if the passive crawl reports out-of-origin URLs."""

    target_origin = _origin_tuple(validate_passive_target_url(target_url))
    text = "\n".join(chunk or "" for chunk in output_chunks)
    for match in re.findall(r"https?://[^\s<>'\"]+", text):
        candidate = match.rstrip(".,);]}")
        try:
            candidate_origin = _origin_tuple(candidate)
        except ZapPassiveError:
            continue
        if candidate_origin != target_origin:
            raise ZapPassiveError("ZAP passive output referenced an out-of-scope URL")


def build_zap_passive_command(
    target_url: str,
    *,
    max_minutes: int = 1,
    zap_binary: str = "zap-baseline.py",
    output_dir: str | Path | None = None,
) -> tuple[str, ...]:
    if not isinstance(max_minutes, int) or isinstance(max_minutes, bool) or max_minutes < 1 or max_minutes > 10:
        raise ZapPassiveError("ZAP passive max_minutes must be from 1 to 10")
    safe_url = validate_passive_target_url(target_url)
    argv = [zap_binary, "-t", safe_url, "-m", str(max_minutes), "-I"]
    if output_dir is not None:
        output = Path(output_dir)
        argv.extend(("-J", str(output / "zap-passive.json"), "-r", str(output / "zap-passive.html")))
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


def run_zap_passive_baseline(
    target_url: str,
    *,
    max_minutes: int = 1,
    runner: ZapRunner = _default_runner,
    timeout_seconds: int = 300,
    zap_binary: str | None = None,
    output_dir: str | Path | None = None,
) -> ToolExecutionResult:
    """Run bounded ZAP baseline in passive mode only."""

    if timeout_seconds < 60 or timeout_seconds > 900:
        raise ZapPassiveError("ZAP passive timeout must be between 60 and 900 seconds")
    binary = zap_binary or shutil.which("zap-baseline.py")
    if binary is None:
        raise ZapPassiveError("zap-baseline.py is not available")
    argv = build_zap_passive_command(
        target_url,
        max_minutes=max_minutes,
        zap_binary=binary,
        output_dir=output_dir,
    )
    try:
        completed = runner(argv, timeout=timeout_seconds)
        validate_zap_output_scope(target_url, completed.stdout or "", completed.stderr or "")
    except (OSError, TimeoutError, subprocess.TimeoutExpired) as exc:
        raise ZapPassiveError("ZAP passive baseline command failed") from exc
    return ToolExecutionResult(
        tool_name="zap_passive_baseline",
        request_count=1,
        result={
            "target_url": validate_passive_target_url(target_url),
            "max_minutes": max_minutes,
            "argv": list(build_zap_passive_command(target_url, max_minutes=max_minutes, zap_binary="zap-baseline.py", output_dir=output_dir)),
            "returncode": int(completed.returncode),
            "stdout": _truncate(completed.stdout or ""),
            "stderr": _truncate(completed.stderr or ""),
            "output_truncated_at_bytes": MAX_OUTPUT_BYTES,
            "scope_enforced": True,
        },
    )
