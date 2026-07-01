"""FOSS tool inventory for Sprint 15 governed native wrappers."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class FossTool:
    name: str
    purpose: str
    command: tuple[str, ...]
    required_for_tools: tuple[str, ...]
    authority_note: str = "availability never grants execution authority"


FOSS_TOOLS: tuple[FossTool, ...] = (
    FossTool(
        name="python3",
        purpose="runtime and constrained shell provenance",
        command=("python3", "--version"),
        required_for_tools=("campaign_shell",),
    ),
    FossTool(
        name="nmap",
        purpose="single-host single-service fingerprint wrapper",
        command=("nmap", "--version"),
        required_for_tools=("nmap_governed",),
    ),
    FossTool(
        name="zap-baseline.py",
        purpose="OWASP ZAP passive baseline wrapper",
        command=("zap-baseline.py", "-h"),
        required_for_tools=("zap_passive_baseline",),
    ),
    FossTool(
        name="playwright",
        purpose="passive browser metadata wrapper",
        command=("playwright", "--version"),
        required_for_tools=("playwright_passive_metadata",),
    ),
)


def _probe(command: tuple[str, ...]) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        return {"available": False, "path": None, "returncode": None, "output": "not found"}
    argv = (executable, *command[1:])
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
    except (OSError, TimeoutError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "path": executable, "returncode": None, "output": str(exc)}
    output = ((completed.stdout or "") + (completed.stderr or "")).strip().splitlines()
    return {
        "available": completed.returncode == 0,
        "path": executable,
        "returncode": int(completed.returncode),
        "output": output[:5],
    }


def generate_foss_tool_inventory(*, probe: bool = True) -> dict[str, Any]:
    """Return availability metadata without changing any tool permission."""

    tools = []
    for item in FOSS_TOOLS:
        record = asdict(item)
        record["command"] = list(item.command)
        record["required_for_tools"] = list(item.required_for_tools)
        record["probe"] = _probe(item.command) if probe else {"available": None}
        tools.append(record)
    return {
        "schema_version": "1.0",
        "authority_note": "tool presence is inventory only and never bypasses ROE, registry, or budget gates",
        "tools": tools,
    }
