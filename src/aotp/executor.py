"""Network-silent deterministic execution boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .verifier import Verdict


@dataclass(frozen=True)
class ExecutionResult:
    verdict: str
    tool: str
    request_count: int
    response_metadata: dict[str, Any]


def execute(objective: dict[str, Any], *, live: bool = False) -> ExecutionResult:
    if live:
        return ExecutionResult(
            Verdict.MANUAL_REVIEW,
            "live-adapter-stub",
            0,
            {"status": "live execution is not implemented; no network request was sent"},
        )
    return ExecutionResult(
        Verdict.INCONCLUSIVE,
        "deterministic-dry-run",
        0,
        {"status": "planned only; no network request was sent", "action": objective.get("action")},
    )
