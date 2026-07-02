"""Evidence-driven WSTG execution planning for generic live campaigns."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from aotp.wstg import WSTGEnginePlan, WSTGPlanDisposition

from .target_runtime import CampaignTargetRuntime, TargetRuntimeError


class ExecutionPlannerError(ValueError):
    """Raised when no safe campaign action can be planned."""


@dataclass(frozen=True)
class CampaignAction:
    """A governed, bounded action proposed by the campaign planner."""

    action_id: str
    action_type: str
    tool_name: str
    method: str
    path: str
    wstg_ids: tuple[str, ...]
    objective_ids: tuple[str, ...]
    reason: str
    requires_human_approval: bool = False
    state_changing: bool = False

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", self.action_id) is None:
            raise ExecutionPlannerError("action_id must be a safe lowercase identifier")
        if self.action_type != "http_get":
            raise ExecutionPlannerError("Sprint 19 generic harness only plans http_get actions")
        if self.method != "GET":
            raise ExecutionPlannerError("Sprint 19 generic harness only allows GET actions")
        if self.state_changing:
            raise ExecutionPlannerError("state-changing actions are not allowed in Sprint 19")
        if self.requires_human_approval:
            raise ExecutionPlannerError("approval-required actions must wait for later controlled action chain support")
        if not self.path.startswith("/") or ".." in self.path.split("/"):
            raise ExecutionPlannerError("action path must be a safe relative path")
        if not self.wstg_ids:
            raise ExecutionPlannerError("action must map to at least one WSTG id")
        if not self.reason.strip():
            raise ExecutionPlannerError("action reason is required")

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "tool_name": self.tool_name,
            "method": self.method,
            "path": self.path,
            "wstg_ids": list(self.wstg_ids),
            "objective_ids": list(self.objective_ids),
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "state_changing": self.state_changing,
        }


@dataclass(frozen=True)
class ExecutionPlan:
    """The next bounded action queue plus skipped objective reasons."""

    actions: tuple[CampaignAction, ...]
    blocked_objectives: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "actions": [action.as_dict() for action in self.actions],
            "blocked_objectives": list(self.blocked_objectives),
        }


def plan_campaign_actions(plan: WSTGEnginePlan, runtime: CampaignTargetRuntime) -> ExecutionPlan:
    """Build a safe action queue from WSTG readiness and target runtime bounds."""

    if not runtime.implemented_live_target:
        raise TargetRuntimeError("target runtime is not live-executable")
    ready_by_id = {item.wstg_id: item for item in plan.ready_tests}
    actions: list[CampaignAction] = []
    for index, path in enumerate(runtime.safe_paths[: runtime.max_actions], start=1):
        # Runtime safe-path observations can support WSTG evidence beyond the initial
        # ready slice. Keep the canonical path mapping as the observation scope, while
        # binding objective_ids only to objectives that are ready in this campaign plan.
        # This prevents the generic harness from losing API or browser evidence merely
        # because a bounded max_ready_tests slice deferred that WSTG objective.
        wstg_ids = _wstg_ids_for_path(path)
        objective_ids = tuple(ready_by_id[wstg_id].objective_id for wstg_id in wstg_ids if wstg_id in ready_by_id)
        actions.append(
            CampaignAction(
                action_id=f"http-get-{index:02d}",
                action_type="http_get",
                tool_name="http_metadata",
                method="GET",
                path=path,
                wstg_ids=wstg_ids,
                objective_ids=objective_ids,
                reason=f"GET {path} is same-origin, read-only, and mapped to executable WSTG discovery evidence",
            )
        )
    blocked = [
        {
            "objective_id": item.objective_id,
            "wstg_id": item.wstg_id,
            "disposition": item.disposition.value,
            "reasons": list(item.reasons),
        }
        for item in plan.planned_tests
        if item.disposition is not WSTGPlanDisposition.READY
    ]
    return ExecutionPlan(actions=tuple(actions), blocked_objectives=tuple(blocked))


def _wstg_ids_for_path(path: str) -> tuple[str, ...]:
    if path == "/":
        return ("WSTG-v42-INFO-02", "WSTG-v42-INFO-05", "WSTG-v42-INFO-08")
    if path in {"/robots.txt", "/sitemap.xml"}:
        return ("WSTG-v42-INFO-03", "WSTG-v42-INFO-06")
    if "/api/" in path.lower() or path.startswith("/rest/"):
        return ("WSTG-v42-INFO-06", "WSTG-v42-APIT-01")
    return ("WSTG-v42-INFO-06",)
