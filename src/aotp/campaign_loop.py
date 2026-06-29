"""Bounded campaign loop with evidence and stop records."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict
from pathlib import Path
from time import monotonic
from typing import Any

from .campaign_state import CampaignEvent, CampaignState, save_state
from .evidence import EvidenceManifest, utc_now, write_manifest
from .executor import execute
from .policy_gate import evaluate
from .safety_budget import SafetyBudget
from .scheduler import schedule
from .verifier import Verdict


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_campaign(
    scope: dict[str, Any],
    scope_path: Path,
    campaign: dict[str, Any],
    *,
    live: bool = False,
    operator_approved: bool = False,
    workspace: Path | None = None,
) -> tuple[CampaignState, Path]:
    root = (workspace or Path.cwd()).resolve()
    now = utc_now()
    objectives = schedule(campaign["objectives"])
    state = CampaignState(
        campaign_id=campaign["campaign_id"],
        campaign_name=campaign["name"],
        scope_file_hash=_hash(scope_path),
        rules_of_engagement_reference=str(scope["rules_of_engagement"].get("reference", "")),
        authorization_reference=str(scope["authorization"].get("reference", "")),
        start_time=now,
        last_updated_time=now,
        current_status="running",
        pending_modules=[str(item["id"]) for item in objectives],
    )
    limits = campaign.get("limits", {})
    budget = SafetyBudget(
        max_iterations=int(limits.get("max_iterations", len(objectives))),
        max_runtime_seconds=int(limits.get("max_runtime_seconds", 60)),
        max_requests=int(scope["rate_limits"]["max_requests"]),
    )
    started = monotonic()
    base_evidence = Path(scope["evidence"]["workspace"])
    if not base_evidence.is_absolute():
        base_evidence = root / base_evidence

    for index, objective in enumerate(objectives, 1):
        objective_id = str(objective["id"])
        if state.operator_stop_requested or not budget.can_continue(monotonic() - started):
            state.current_status = "stopped"
            state.stop_condition_history.append("operator or safety budget stop")
            break
        decision = evaluate(
            scope,
            objective,
            live=live,
            operator_approved=operator_approved,
            workspace=root,
        )
        iteration_id = f"{index:04d}"
        evidence_dir = base_evidence / state.campaign_id / iteration_id
        if decision.allowed:
            result = execute(objective, live=live)
            outcome = result.verdict
            if result.verdict == Verdict.MANUAL_REVIEW:
                state.current_status = "paused_for_human_review"
                state.stop_condition_history.append(f"{objective_id}: human review required")
            else:
                state.completed_modules.append(objective_id)
        else:
            result = None
            outcome = Verdict.STOPPED_BY_POLICY
            state.stopped_modules.append(objective_id)
            state.current_status = "stopped_by_policy"
            state.stop_condition_history.extend(decision.reasons)

        manifest = EvidenceManifest(
            run_id=str(uuid.uuid4()),
            timestamp_utc=utc_now(),
            operator=str(scope.get("operator_alias", "operator")),
            sponsor_alias=scope["sponsor_alias"],
            target_alias=str(objective.get("target_alias", "none")),
            authorization_reference=str(scope["authorization"].get("reference", "")),
            rules_of_engagement_reference=str(scope["rules_of_engagement"].get("reference", "")),
            confidentiality_reference=scope["authorization"].get("confidentiality", {}).get("reference"),
            case_id=objective_id,
            tool=result.tool if result else "policy-gate",
            verifier_verdict=str(outcome),
            confidence="not_assessed",
            campaign_id=state.campaign_id,
            campaign_iteration_id=iteration_id,
            parent_test_objective=str(objective.get("title", objective_id)),
            module_name=str(objective.get("module", "")),
            wstg_mapping=list(objective.get("wstg_mapping", [])),
            artifact_mapping=list(objective.get("artifact_mapping", [])),
            target_category=str(objective.get("target_category", "placeholder")),
            execution_mode="live_stub" if live else "dry_run",
            policy_decision=decision.summary,
            request_count=result.request_count if result else 0,
            response_metadata=result.response_metadata if result else {"policy_reasons": list(decision.reasons)},
        )
        write_manifest(manifest, evidence_dir)
        state.evidence_directories.append(str(evidence_dir.relative_to(root)))
        state.pending_modules.remove(objective_id)
        state.request_counters["total"] += manifest.request_count
        budget.record(manifest.request_count)
        event = CampaignEvent(
            iteration_id,
            utc_now(),
            objective_id,
            str(objective.get("module", "")),
            decision.summary,
            str(outcome),
            str(evidence_dir.relative_to(root)),
        )
        state.events.append(asdict(event))
        state.last_updated_time = utc_now()
        if state.current_status != "running":
            break

    if state.current_status == "running":
        state.current_status = "completed" if not state.pending_modules else "stopped"
    state_path = root / ".aotp" / "state" / f"{state.campaign_id}.json"
    save_state(state, state_path)
    return state, state_path
