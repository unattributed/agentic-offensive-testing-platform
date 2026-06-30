"""Checkpointed deterministic campaign execution."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from pathlib import Path
from time import monotonic
from typing import Any, Callable

from .campaign import parse_campaign
from .campaign_state import CampaignEvent, CampaignState, save_state
from .evidence import EvidenceManifest, utc_now, write_manifest
from .executor import execute
from .policy_gate import evaluate
from .safety_budget import SafetyBudget
from .scheduler import schedule
from .verifier import Verdict


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _run_id(state: CampaignState, iteration_id: str, objective_id: str) -> str:
    stable_key = f"{state.campaign_id}:{state.scope_file_hash}:{iteration_id}:{objective_id}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, stable_key))


def _initialize_state(
    scope: dict[str, Any],
    scope_path: Path,
    campaign: dict[str, Any],
) -> CampaignState:
    parsed = parse_campaign(campaign)
    now = utc_now()
    objectives = schedule(campaign["objectives"])
    return CampaignState(
        campaign_id=parsed.campaign_id,
        campaign_name=parsed.name,
        campaign_definition_hash=_mapping_hash(campaign),
        scope_file_hash=_file_hash(scope_path),
        rules_of_engagement_reference=str(scope["rules_of_engagement"].get("reference", "")),
        authorization_reference=str(scope["authorization"].get("reference", "")),
        operator_alias=str(scope.get("operator_alias", "operator")),
        start_time=now,
        last_updated_time=now,
        current_status="planned",
        pending_modules=[str(item["id"]) for item in objectives],
    )


def _validate_resume_inputs(
    state: CampaignState,
    scope_path: Path,
    campaign: dict[str, Any],
) -> None:
    if state.scope_file_hash != _file_hash(scope_path):
        raise ValueError("scope file hash does not match campaign state")
    if state.campaign_definition_hash != _mapping_hash(campaign):
        raise ValueError("campaign definition hash does not match campaign state")
    campaign_ids = {str(item["id"]) for item in campaign["objectives"]}
    state_ids = (
        set(state.completed_modules)
        | set(state.pending_modules)
        | set(state.skipped_modules)
        | set(state.stopped_modules)
    )
    if not state_ids <= campaign_ids:
        raise ValueError("campaign state contains objectives absent from campaign definition")
    if state.current_status not in {"running", "ready_to_resume", "planned"}:
        raise ValueError(f"campaign state cannot execute from status: {state.current_status}")


def _record_pre_execution_stop(
    *,
    state: CampaignState,
    scope: dict[str, Any],
    objective: dict[str, Any],
    reason: str,
    root: Path,
    base_evidence: Path,
) -> None:
    objective_id = str(objective["id"])
    iteration_id = f"{state.next_iteration:04d}"
    evidence_dir = base_evidence / state.campaign_id / iteration_id
    manifest = EvidenceManifest(
        run_id=_run_id(state, iteration_id, objective_id),
        timestamp_utc=utc_now(),
        operator=str(scope.get("operator_alias", "operator")),
        sponsor_alias=scope["sponsor_alias"],
        target_alias=str(objective.get("target_alias", "none")),
        authorization_reference=str(scope["authorization"].get("reference", "")),
        rules_of_engagement_reference=str(scope["rules_of_engagement"].get("reference", "")),
        confidentiality_reference=scope["authorization"].get("confidentiality", {}).get("reference"),
        case_id=objective_id,
        tool="safety-budget",
        verifier_verdict=str(Verdict.STOPPED_BY_POLICY),
        confidence="not_assessed",
        campaign_id=state.campaign_id,
        campaign_iteration_id=iteration_id,
        parent_test_objective=str(objective.get("title", objective_id)),
        module_name=str(objective.get("module", "")),
        wstg_mapping=list(objective.get("wstg_mapping", [])),
        artifact_mapping=list(objective.get("artifact_mapping", [])),
        target_category=str(objective.get("target_category", "placeholder")),
        execution_mode="not_executed",
        policy_decision=f"stopped by {reason}",
        request_count=0,
        response_metadata={"stop_condition": reason},
    )
    write_manifest(manifest, evidence_dir)
    relative_evidence = str(evidence_dir.relative_to(root))
    state.evidence_directories.append(relative_evidence)
    state.pending_modules.remove(objective_id)
    state.stopped_modules.append(objective_id)
    state.current_objective_id = None
    state.stop_condition_history.append(reason)
    state.next_iteration += 1
    state.events.append(
        asdict(
            CampaignEvent(
                sequence=len(state.events) + 1,
                event_id=str(uuid.uuid4()),
                iteration_id=iteration_id,
                timestamp_utc=utc_now(),
                event_type="campaign_stop",
                objective_id=objective_id,
                module_name=str(objective.get("module", "")),
                policy_decision=f"stopped by {reason}",
                outcome=str(Verdict.STOPPED_BY_POLICY),
                evidence_directory=relative_evidence,
                details={"stop_condition": reason},
            )
        )
    )


def run_campaign(
    scope: dict[str, Any],
    scope_path: Path,
    campaign: dict[str, Any],
    *,
    program_profile: dict[str, Any] | None = None,
    operator_approval: dict[str, Any] | None = None,
    live: bool = False,
    operator_approved: bool = False,
    workspace: Path | None = None,
    state: CampaignState | None = None,
    state_path: Path | None = None,
    max_steps: int | None = None,
    clock: Callable[[], float] = monotonic,
) -> tuple[CampaignState, Path]:
    parsed = parse_campaign(campaign)
    root = (workspace or Path.cwd()).resolve()
    state = state or _initialize_state(scope, scope_path, campaign)
    _validate_resume_inputs(state, scope_path, campaign)
    state_path = state_path or root / ".aotp" / "state" / f"{state.campaign_id}.json"
    state.current_status = "running"
    state.last_updated_time = utc_now()
    save_state(state, state_path)

    budget = SafetyBudget(
        max_iterations=parsed.limits.max_iterations,
        max_runtime_seconds=parsed.limits.max_runtime_seconds,
        max_requests=min(parsed.limits.max_requests, int(scope["rate_limits"]["max_requests"])),
        max_requests_per_minute=int(scope["rate_limits"]["requests_per_minute"]),
        max_consecutive_failures=parsed.limits.max_consecutive_failures,
        iterations=state.next_iteration - 1,
        requests=state.request_counters["total"],
        current_minute_requests=state.rate_limit_counters["current_minute"],
        consecutive_failures=state.consecutive_failures,
    )
    invocation_started = clock()
    elapsed_before_invocation = state.elapsed_seconds
    base_evidence = Path(scope["evidence"]["workspace"])
    if not base_evidence.is_absolute():
        base_evidence = root / base_evidence
    ordered = schedule(campaign["objectives"])
    steps = 0

    for configured_objective in ordered:
        objective = dict(configured_objective)
        objective_id = str(objective["id"])
        if objective_id not in state.pending_modules:
            continue
        if objective_id in state.reviewed_objectives:
            objective["human_approved"] = True
        if max_steps is not None and steps >= max_steps:
            break
        elapsed = elapsed_before_invocation + (clock() - invocation_started)
        proposed_requests = int(objective["parameters"]["request_budget"])
        budget_reason = budget.denial_reason(
            elapsed_seconds=elapsed,
            proposed_requests=proposed_requests,
        )
        if state.operator_stop_requested or budget_reason:
            stop_reason = "operator_stop" if state.operator_stop_requested else str(budget_reason)
            state.current_status = (
                "stopped_by_operator" if state.operator_stop_requested else "stopped_by_budget"
            )
            _record_pre_execution_stop(
                state=state,
                scope=scope,
                objective=objective,
                reason=stop_reason,
                root=root,
                base_evidence=base_evidence,
            )
            break

        iteration_id = f"{state.next_iteration:04d}"
        state.current_objective_id = objective_id
        state.last_updated_time = utc_now()
        save_state(state, state_path)
        decision = evaluate(
            scope,
            objective,
            program_profile=program_profile,
            operator_approval=operator_approval,
            scope_sha256=state.scope_file_hash,
            campaign_id=state.campaign_id,
            live=live,
            operator_approved=operator_approved,
            workspace=root,
        )
        evidence_dir = base_evidence / state.campaign_id / iteration_id
        human_gate_only = (
            not decision.allowed and decision.reasons == ("human approval is required",)
        )
        if decision.allowed:
            result = execute(objective, live=live)
            outcome = result.verdict
        elif human_gate_only:
            result = None
            outcome = Verdict.MANUAL_REVIEW
        else:
            result = None
            outcome = Verdict.STOPPED_BY_POLICY

        manifest = EvidenceManifest(
            run_id=_run_id(state, iteration_id, objective_id),
            timestamp_utc=utc_now(),
            operator=str(scope.get("operator_alias", "operator")),
            sponsor_alias=scope["sponsor_alias"],
            target_alias=str(objective.get("target_alias", "none")),
            authorization_reference=str(scope["authorization"].get("reference", "")),
            rules_of_engagement_reference=str(scope["rules_of_engagement"].get("reference", "")),
            confidentiality_reference=scope["authorization"].get("confidentiality", {}).get("reference"),
            case_id=objective_id,
            tool=(
                result.tool
                if result
                else "human-approval-gate"
                if human_gate_only
                else "policy-gate"
            ),
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
            response_metadata=(
                result.response_metadata if result else {"policy_reasons": list(decision.reasons)}
            ),
        )
        write_manifest(manifest, evidence_dir)
        relative_evidence = str(evidence_dir.relative_to(root))
        if relative_evidence not in state.evidence_directories:
            state.evidence_directories.append(relative_evidence)
        state.request_counters["total"] += manifest.request_count
        budget.record(
            manifest.request_count,
            failed=outcome in {Verdict.FAIL, Verdict.STOPPED_BY_POLICY},
        )
        state.rate_limit_counters["current_minute"] = budget.current_minute_requests
        state.consecutive_failures = budget.consecutive_failures

        event = CampaignEvent(
            sequence=len(state.events) + 1,
            event_id=str(uuid.uuid4()),
            iteration_id=iteration_id,
            timestamp_utc=utc_now(),
            event_type="objective_result",
            objective_id=objective_id,
            module_name=str(objective.get("module", "")),
            policy_decision=decision.summary,
            outcome=str(outcome),
            evidence_directory=relative_evidence,
        )
        state.events.append(asdict(event))
        state.next_iteration += 1
        steps += 1

        if human_gate_only:
            state.current_status = "paused_for_human_review"
            state.pending_review = {
                "objective_id": objective_id,
                "phase": "pre_execution",
                "reason": "human approval is required",
                "evidence_directory": relative_evidence,
            }
            state.stop_condition_history.append(f"{objective_id}: human approval required")
        elif not decision.allowed:
            state.pending_modules.remove(objective_id)
            state.stopped_modules.append(objective_id)
            state.current_objective_id = None
            state.current_status = "stopped_by_policy"
            state.stop_condition_history.extend(decision.reasons)
        elif outcome == Verdict.MANUAL_REVIEW:
            state.current_status = "paused_for_human_review"
            state.pending_review = {
                "objective_id": objective_id,
                "phase": "post_execution",
                "reason": "manual review required after adapter execution",
                "evidence_directory": relative_evidence,
            }
            state.stop_condition_history.append(f"{objective_id}: human review required")
        else:
            state.pending_modules.remove(objective_id)
            state.completed_modules.append(objective_id)
            state.current_objective_id = None
            state.current_status = "running"

        state.elapsed_seconds = elapsed_before_invocation + (clock() - invocation_started)
        state.last_updated_time = utc_now()
        save_state(state, state_path)
        if state.current_status != "running":
            break

    state.elapsed_seconds = elapsed_before_invocation + (clock() - invocation_started)
    if state.current_status == "running" and not state.pending_modules:
        state.current_status = "completed"
        state.current_objective_id = None
    state.last_updated_time = utc_now()
    save_state(state, state_path)
    return state, state_path
