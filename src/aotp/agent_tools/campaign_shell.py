"""Constrained Parrot campaign shell wrapper."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol

from .http_metadata import ToolExecutionResult


MAX_OUTPUT_BYTES = 16_384


class CampaignShellError(RuntimeError):
    """Raised when the constrained campaign shell cannot execute safely."""


class CommandRunner(Protocol):
    def __call__(
        self,
        argv: tuple[str, ...],
        *,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]: ...


@dataclass(frozen=True)
class ShellCommandSpec:
    command_id: str
    argv: tuple[str, ...]
    description: str


ALLOWED_COMMANDS: dict[str, ShellCommandSpec] = {
    "python-version": ShellCommandSpec(
        command_id="python-version",
        argv=("python3", "--version"),
        description="record the Python runtime version",
    ),
    "nmap-version": ShellCommandSpec(
        command_id="nmap-version",
        argv=("nmap", "--version"),
        description="record nmap availability and version",
    ),
    "zap-baseline-help": ShellCommandSpec(
        command_id="zap-baseline-help",
        argv=("zap-baseline.py", "-h"),
        description="record OWASP ZAP baseline wrapper availability",
    ),
    "playwright-version": ShellCommandSpec(
        command_id="playwright-version",
        argv=("python3", "-m", "playwright", "--version"),
        description="record Playwright Python availability and version",
    ),
}


def list_allowed_shell_commands() -> tuple[ShellCommandSpec, ...]:
    """Return the immutable allowlist for the constrained campaign shell."""

    return tuple(ALLOWED_COMMANDS[name] for name in sorted(ALLOWED_COMMANDS))


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


def run_campaign_shell_command(
    command_id: str,
    *,
    runner: CommandRunner = _default_runner,
    timeout_seconds: int = 15,
) -> ToolExecutionResult:
    """Execute one fixed local command by identifier, never arbitrary argv."""

    spec = ALLOWED_COMMANDS.get(command_id)
    if spec is None:
        raise CampaignShellError("campaign shell command is not allowlisted")
    if timeout_seconds < 1 or timeout_seconds > 60:
        raise CampaignShellError("campaign shell timeout must be between 1 and 60 seconds")
    executable = shutil.which(spec.argv[0]) or spec.argv[0]
    argv = (executable, *spec.argv[1:])
    try:
        completed = runner(argv, timeout=timeout_seconds)
    except (OSError, TimeoutError, subprocess.TimeoutExpired) as exc:
        raise CampaignShellError("allowlisted campaign shell command failed") from exc
    result: dict[str, Any] = {
        "command_id": spec.command_id,
        "description": spec.description,
        "argv": list(spec.argv),
        "returncode": int(completed.returncode),
        "stdout": _truncate(completed.stdout or ""),
        "stderr": _truncate(completed.stderr or ""),
        "output_truncated_at_bytes": MAX_OUTPUT_BYTES,
    }
    return ToolExecutionResult(
        tool_name="campaign_shell",
        request_count=0,
        result=result,
    )
