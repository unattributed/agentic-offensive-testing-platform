"""Network-silent deterministic execution boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .control_panel import build_panel_dry_run_observation_plan
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
    if (
        objective.get("category") == "service_control_panel"
        and (
            objective.get("action") == "plan_safe_panel_observations"
            or objective.get("requested_observations")
        )
    ):
        plan = build_panel_dry_run_observation_plan(objective)
        return ExecutionResult(
            Verdict.INCONCLUSIVE,
            "control-panel-dry-run-planner",
            0,
            {
                "status": "safe panel observations planned only; no network request was sent",
                "observation_plan": plan,
            },
        )
    return ExecutionResult(
        Verdict.INCONCLUSIVE,
        "deterministic-dry-run",
        0,
        {"status": "planned only; no network request was sent", "action": objective.get("action")},
    )
