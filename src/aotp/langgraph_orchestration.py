"""Durable LangGraph orchestration around the deterministic campaign engine."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Literal, TypedDict

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, interrupt
    _LANGGRAPH_AVAILABLE = True
except ModuleNotFoundError:
    _LANGGRAPH_AVAILABLE = False
    END = "__end__"
    START = "__start__"

    class Command:  # type: ignore[no-redef]
        def __init__(self, *, resume: dict[str, Any]) -> None:
            self.resume = resume

    def interrupt(payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    class SqliteSaver:  # type: ignore[no-redef]
        def __init__(self, connection: sqlite3.Connection) -> None:
            self.connection = connection

        def setup(self) -> None:
            return None

    class StateGraph:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("langgraph is required for native graph execution")

from .campaign import parse_campaign
from .campaign_control import apply_review_decision
from .campaign_loop import run_campaign
from .campaign_state import load_state
from .evidence import sha256_file


TERMINAL_STATUSES = {
    "completed",
    "stopped_by_policy",
    "stopped_by_operator",
    "stopped_by_budget",
    "stopped_by_condition",
    "failed",
}


class GraphCampaignState(TypedDict):
    campaign_id: str
    scope_sha256: str
    campaign_sha256: str
    aotp_state_path: str
    status: str
    current_objective_id: str | None
    steps: int


def _mapping_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class LangGraphCampaignOrchestrator:
    """Run one deterministic AOTP objective per durable LangGraph step."""

    def __init__(
        self,
        *,
        scope: dict[str, Any],
        scope_path: Path,
        campaign: dict[str, Any],
        workspace: Path,
        program_profile: dict[str, Any] | None = None,
        operator_approval: dict[str, Any] | None = None,
        live: bool = False,
        operator_approved: bool = False,
        checkpoint_db: Path | None = None,
    ) -> None:
        parsed = parse_campaign(campaign)
        self.scope = scope
        self.scope_path = scope_path.resolve()
        self.campaign = campaign
        self.workspace = workspace.resolve()
        self.program_profile = program_profile
        self.operator_approval = operator_approval
        self.live = live
        self.operator_approved = operator_approved
        self.scope_sha256 = sha256_file(self.scope_path)
        self.campaign_sha256 = _mapping_hash(campaign)
        self.state_path = self.workspace / ".aotp" / "state" / f"{parsed.campaign_id}.json"
        self.checkpoint_db = (
            checkpoint_db.resolve()
            if checkpoint_db
            else self.workspace / ".aotp" / "checkpoints" / f"{parsed.campaign_id}.sqlite"
        )
        try:
            self.checkpoint_db.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("LangGraph checkpoint database must stay within workspace") from exc
        self.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.checkpoint_db.parent, 0o700)
        self.connection = sqlite3.connect(self.checkpoint_db, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.checkpointer = SqliteSaver(self.connection)
        self.checkpointer.setup()
        if not _LANGGRAPH_AVAILABLE:
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS aotp_checkpoint "
                "(thread_id TEXT PRIMARY KEY, state_json TEXT NOT NULL)"
            )
            self.connection.commit()
        self.thread_id = f"{parsed.campaign_id}:{self.scope_sha256[:16]}"
        self.config = {
            "configurable": {"thread_id": self.thread_id},
            "recursion_limit": parsed.limits.max_iterations * 4 + 20,
        }
        self.graph = self._build_graph() if _LANGGRAPH_AVAILABLE else None
        self._secure_checkpoint_files()

    def _secure_checkpoint_files(self) -> None:
        for path in (
            self.checkpoint_db,
            Path(str(self.checkpoint_db) + "-wal"),
            Path(str(self.checkpoint_db) + "-shm"),
        ):
            if path.exists():
                os.chmod(path, 0o600)

    def _build_graph(self):
        builder = StateGraph(GraphCampaignState)
        builder.add_node("campaign_step", self._campaign_step)
        builder.add_node("human_review", self._human_review)
        builder.add_edge(START, "campaign_step")
        builder.add_conditional_edges(
            "campaign_step",
            self._route_after_step,
            {
                "continue": "campaign_step",
                "review": "human_review",
                "end": END,
            },
        )
        builder.add_conditional_edges(
            "human_review",
            self._route_after_review,
            {"continue": "campaign_step", "end": END},
        )
        return builder.compile(checkpointer=self.checkpointer, name="aotp-campaign")

    def _campaign_step(self, graph_state: GraphCampaignState) -> dict[str, Any]:
        if self.state_path.exists():
            state = load_state(self.state_path)
            if state.current_status in TERMINAL_STATUSES:
                return {
                    "status": state.current_status,
                    "current_objective_id": state.current_objective_id,
                }
            state_arg = state
        else:
            state_arg = None
        state, _ = run_campaign(
            self.scope,
            self.scope_path,
            self.campaign,
            program_profile=self.program_profile,
            operator_approval=self.operator_approval,
            live=self.live,
            operator_approved=self.operator_approved,
            workspace=self.workspace,
            state=state_arg,
            state_path=self.state_path,
            max_steps=1,
        )
        return {
            "status": state.current_status,
            "current_objective_id": state.current_objective_id,
            "steps": graph_state.get("steps", 0) + 1,
        }

    def _human_review(self, graph_state: GraphCampaignState) -> dict[str, Any]:
        state = load_state(self.state_path)
        review = interrupt(
            {
                "campaign_id": state.campaign_id,
                "objective_id": state.current_objective_id,
                "operator_alias": state.operator_alias,
                "state_path": str(self.state_path),
                "required": "private review decision bound to current state SHA256",
            }
        )
        if not isinstance(review, dict):
            raise ValueError("LangGraph review resume value must be a review mapping")
        apply_review_decision(state, self.state_path, review)
        return {
            "status": state.current_status,
            "current_objective_id": state.current_objective_id,
            "steps": graph_state.get("steps", 0),
        }

    @staticmethod
    def _route_after_step(
        state: GraphCampaignState,
    ) -> Literal["continue", "review", "end"]:
        if state["status"] == "running":
            return "continue"
        if state["status"] == "paused_for_human_review":
            return "review"
        return "end"

    @staticmethod
    def _route_after_review(state: GraphCampaignState) -> Literal["continue", "end"]:
        return "continue" if state["status"] == "ready_to_resume" else "end"

    def _initial_state(self) -> GraphCampaignState:
        return {
            "campaign_id": parse_campaign(self.campaign).campaign_id,
            "scope_sha256": self.scope_sha256,
            "campaign_sha256": self.campaign_sha256,
            "aotp_state_path": str(self.state_path),
            "status": "planned",
            "current_objective_id": None,
            "steps": 0,
        }

    def _verify_checkpoint_inputs(self) -> None:
        if _LANGGRAPH_AVAILABLE:
            if self.graph is None:
                raise ValueError("LangGraph graph is not initialized")
            snapshot = self.graph.get_state(self.config)
            values = snapshot.values
        else:
            values = self._fallback_snapshot_values()
        if not values:
            return
        if values.get("scope_sha256") != self.scope_sha256:
            raise ValueError("LangGraph checkpoint scope hash does not match current scope")
        if values.get("campaign_sha256") != self.campaign_sha256:
            raise ValueError("LangGraph checkpoint campaign hash does not match current campaign")

    def start(self) -> dict[str, Any]:
        if _LANGGRAPH_AVAILABLE:
            if self.graph is None:
                raise ValueError("LangGraph graph is not initialized")
            snapshot = self.graph.get_state(self.config)
            if snapshot.values:
                raise ValueError("LangGraph campaign thread already exists; use resume")
            self.graph.invoke(self._initial_state(), self.config)
            self._secure_checkpoint_files()
            return dict(self.graph.get_state(self.config).values)
        if self._fallback_snapshot_values():
            raise ValueError("LangGraph campaign thread already exists; use resume")
        state, _ = run_campaign(
            self.scope,
            self.scope_path,
            self.campaign,
            program_profile=self.program_profile,
            operator_approval=self.operator_approval,
            live=self.live,
            operator_approved=self.operator_approved,
            workspace=self.workspace,
            state_path=self.state_path,
        )
        snapshot = self._snapshot_from_campaign_state(state, steps=max(0, state.next_iteration - 1))
        self._fallback_save_snapshot(snapshot)
        self._secure_checkpoint_files()
        return snapshot

    def resume(self, review: dict[str, Any]) -> dict[str, Any]:
        self._verify_checkpoint_inputs()
        if _LANGGRAPH_AVAILABLE:
            if self.graph is None:
                raise ValueError("LangGraph graph is not initialized")
            snapshot = self.graph.get_state(self.config)
            if "human_review" not in snapshot.next:
                raise ValueError("LangGraph campaign is not waiting for human review")
            self.graph.invoke(Command(resume=review), self.config)
            self._secure_checkpoint_files()
            return dict(self.graph.get_state(self.config).values)
        snapshot = self._fallback_snapshot_values()
        if snapshot.get("status") != "paused_for_human_review":
            raise ValueError("LangGraph campaign is not waiting for human review")
        state = load_state(self.state_path)
        apply_review_decision(state, self.state_path, review)
        state, _ = run_campaign(
            self.scope,
            self.scope_path,
            self.campaign,
            program_profile=self.program_profile,
            operator_approval=self.operator_approval,
            live=self.live,
            operator_approved=self.operator_approved,
            workspace=self.workspace,
            state=load_state(self.state_path),
            state_path=self.state_path,
        )
        resumed = self._snapshot_from_campaign_state(state, steps=int(snapshot.get("steps", 0)) + 1)
        self._fallback_save_snapshot(resumed)
        self._secure_checkpoint_files()
        return resumed

    def snapshot(self) -> dict[str, Any]:
        self._verify_checkpoint_inputs()
        if _LANGGRAPH_AVAILABLE:
            if self.graph is None:
                raise ValueError("LangGraph graph is not initialized")
            return dict(self.graph.get_state(self.config).values)
        return self._fallback_snapshot_values()

    def _fallback_snapshot_values(self) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT state_json FROM aotp_checkpoint WHERE thread_id = ?",
            (self.thread_id,),
        ).fetchone()
        if row is None:
            return {}
        return dict(json.loads(row[0]))

    def _fallback_save_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO aotp_checkpoint(thread_id, state_json) VALUES (?, ?)",
            (self.thread_id, json.dumps(snapshot, sort_keys=True, separators=(",", ":"))),
        )
        self.connection.commit()

    def _snapshot_from_campaign_state(self, state: Any, *, steps: int) -> dict[str, Any]:
        return {
            "campaign_id": state.campaign_id,
            "scope_sha256": self.scope_sha256,
            "campaign_sha256": self.campaign_sha256,
            "aotp_state_path": str(self.state_path),
            "status": state.current_status,
            "current_objective_id": state.current_objective_id,
            "steps": steps,
        }

    def close(self) -> None:
        self.connection.close()
        self._secure_checkpoint_files()

    def __enter__(self) -> "LangGraphCampaignOrchestrator":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
