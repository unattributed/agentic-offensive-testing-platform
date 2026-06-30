"""Checkpointed deterministic campaign execution."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from time import monotonic
from typing import Any, Callable

from .campaign import parse_campaign
from .campaign_events import append_campaign_event, resolve_event_log, verify_state_event_log
from .campaign_state import CampaignState, save_state
from .bounded_fuzzing import collect_fuzzing_stop_signals
from .control_panel import panel_lockout_risk_detected
from .evidence import EvidenceManifest, register_artifact, utc_now, write_manifest
from .executor import execute
from .panel_evidence import write_panel_evidence_record
from .fuzzing_evidence import write_fuzzing_evidence_record
from .sbom_review import write_sbom_record
from .crypto_review import write_crypto_record
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
        event_log_path=f".aotp/events/{parsed.campaign_id}.jsonl",
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
    state_path: Path,
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
    append_campaign_event(
        state,
        state_path,
        event_type="campaign_stop",
        iteration_id=iteration_id,
        objective_id=objective_id,
        module_name=str(objective.get("module", "")),
        policy_decision=f"stopped by {reason}",
        outcome=str(Verdict.STOPPED_BY_POLICY),
        evidence_directory=relative_evidence,
        details={"stop_condition": reason},
    )


def _record_panel_lockout_pause(
    *,
    state: CampaignState,
    scope: dict[str, Any],
    objective: dict[str, Any],
    root: Path,
    base_evidence: Path,
    state_path: Path,
) -> None:
    objective_id = str(objective["id"])
    iteration_id = f"{state.next_iteration:04d}"
    evidence_dir = base_evidence / state.campaign_id / iteration_id
    reason = "authentication_lockout_risk"
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
        tool="panel-lockout-risk-gate",
        verifier_verdict=str(Verdict.MANUAL_REVIEW),
        confidence="not_assessed",
        campaign_id=state.campaign_id,
        campaign_iteration_id=iteration_id,
        parent_test_objective=str(objective.get("title", objective_id)),
        module_name=str(objective.get("module", "")),
        artifact_mapping=list(objective.get("artifact_mapping", [])),
        target_category=str(objective.get("target_category", "placeholder")),
        execution_mode="not_executed",
        policy_decision=f"paused by {reason}",
        request_count=0,
        response_metadata={
            "stop_condition": reason,
            "status": "paused before execution for explicit human review",
        },
    )
    write_manifest(manifest, evidence_dir)
    relative_evidence = str(evidence_dir.relative_to(root))
    state.evidence_directories.append(relative_evidence)
    state.current_objective_id = objective_id
    state.current_status = "paused_for_human_review"
    state.pending_review = {
        "objective_id": objective_id,
        "phase": "pre_execution",
        "reason": "authentication lockout risk requires human review",
        "stop_condition": reason,
        "evidence_directory": relative_evidence,
    }
    state.stop_condition_history.append(f"{objective_id}: {reason}")
    state.next_iteration += 1
    append_campaign_event(
        state,
        state_path,
        event_type="campaign_paused",
        iteration_id=iteration_id,
        objective_id=objective_id,
        module_name=str(objective.get("module", "")),
        policy_decision=f"paused by {reason}",
        outcome="paused_for_human_review",
        evidence_directory=relative_evidence,
        details={"phase": "pre_execution", "stop_condition": reason},
    )


def _record_fuzzing_condition_stop(
    *,
    state: CampaignState,
    scope: dict[str, Any],
    objective: dict[str, Any],
    signals: tuple[str, ...],
    root: Path,
    base_evidence: Path,
    state_path: Path,
) -> None:
    objective_id = str(objective["id"])
    iteration_id = f"{state.next_iteration:04d}"
    evidence_dir = base_evidence / state.campaign_id / iteration_id
    ordered_signals = sorted(signals)
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
        tool="bounded-fuzzing-safety-stop",
        verifier_verdict=str(Verdict.STOPPED_BY_POLICY),
        confidence="not_assessed",
        campaign_id=state.campaign_id,
        campaign_iteration_id=iteration_id,
        parent_test_objective=str(objective.get("title", objective_id)),
        module_name="bounded_fuzzing",
        artifact_mapping=list(objective.get("artifact_mapping", [])),
        target_category=str(objective.get("target_category", "placeholder")),
        execution_mode="not_executed",
        policy_decision="stopped by fuzzing safety condition",
        request_count=0,
        response_metadata={
            "stop_conditions": ordered_signals,
            "request_counters": dict(state.request_counters),
            "endpoint_request_counters": dict(state.endpoint_request_counters),
            "rate_limit_counters": dict(state.rate_limit_counters),
            "consecutive_failures": state.consecutive_failures,
        },
    )
    write_manifest(manifest, evidence_dir)
    relative_evidence = str(evidence_dir.relative_to(root))
    state.evidence_directories.append(relative_evidence)
    state.pending_modules.remove(objective_id)
    state.stopped_modules.append(objective_id)
    state.current_objective_id = None
    state.current_status = "stopped_by_condition"
    state.stop_condition_history.extend(ordered_signals)
    state.next_iteration += 1
    append_campaign_event(
        state,
        state_path,
        event_type="campaign_stop",
        iteration_id=iteration_id,
        objective_id=objective_id,
        module_name="bounded_fuzzing",
        policy_decision="stopped by fuzzing safety condition",
        outcome="stopped_by_condition",
        evidence_directory=relative_evidence,
        details={
            "stop_conditions": ordered_signals,
            "request_counters": dict(state.request_counters),
            "endpoint_request_counters": dict(state.endpoint_request_counters),
            "rate_limit_counters": dict(state.rate_limit_counters),
        },
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
    fresh_campaign = state is None
    state = state or _initialize_state(scope, scope_path, campaign)
    _validate_resume_inputs(state, scope_path, campaign)
    state_path = state_path or root / ".aotp" / "state" / f"{state.campaign_id}.json"
    if fresh_campaign and state_path.exists():
        raise ValueError("campaign state already exists; use campaign-resume or choose a new campaign id")
    if fresh_campaign and resolve_event_log(state, state_path).exists():
        raise ValueError("campaign event log already exists; choose a new campaign id")
    prior_status = state.current_status
    if state.events:
        event_failures = verify_state_event_log(state, state_path)
        if event_failures:
            raise ValueError("campaign event log verification failed: " + "; ".join(event_failures))
    else:
        append_campaign_event(
            state,
            state_path,
            event_type="campaign_started",
            outcome="planned",
            details={"campaign_definition_hash": state.campaign_definition_hash},
        )
    if prior_status == "ready_to_resume":
        append_campaign_event(
            state,
            state_path,
            event_type="campaign_resumed",
            outcome="running",
        )
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
        if (
            objective.get("category") == "sbom_review"
            and isinstance(objective.get("artifact"), str)
        ):
            candidates = [
                (root / objective["artifact"]).resolve(),
                (scope_path.parent / objective["artifact"]).resolve(),
                (scope_path.parent.parent / objective["artifact"]).resolve(),
            ]
            artifact_path = next((path for path in candidates if path.is_file()), candidates[0])
            objective["_resolved_artifact_path"] = str(artifact_path)
        if max_steps is not None and steps >= max_steps:
            break
        fuzzing_stop_signals = collect_fuzzing_stop_signals(objective)
        if fuzzing_stop_signals:
            _record_fuzzing_condition_stop(
                state=state,
                scope=scope,
                objective=objective,
                signals=fuzzing_stop_signals,
                root=root,
                base_evidence=base_evidence,
                state_path=state_path,
            )
            state.last_updated_time = utc_now()
            save_state(state, state_path)
            break
        if (
            panel_lockout_risk_detected(objective)
            and objective_id not in state.reviewed_objectives
        ):
            _record_panel_lockout_pause(
                state=state,
                scope=scope,
                objective=objective,
                root=root,
                base_evidence=base_evidence,
                state_path=state_path,
            )
            state.last_updated_time = utc_now()
            save_state(state, state_path)
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
                state_path=state_path,
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
        if (
            result
            and objective.get("category") == "service_control_panel"
            and isinstance(result.response_metadata, dict)
            and isinstance(result.response_metadata.get("observation_plan"), dict)
        ):
            panel_record_path = write_panel_evidence_record(
                objective,
                evidence_dir,
                policy_decision=decision.summary,
                execution_mode="live_stub" if live else "dry_run",
                tool=result.tool,
                request_count=result.request_count,
                response_metadata=result.response_metadata,
            )
            register_artifact(
                manifest,
                evidence_dir,
                panel_record_path,
                role="service_control_panel_evidence_record",
                artifact_id="panel-evidence-record",
                redaction_status="passed",
            )
        if (
            result
            and objective.get("category") == "bounded_fuzzing"
            and isinstance(result.response_metadata, dict)
            and isinstance(result.response_metadata.get("fuzzing_plan"), dict)
        ):
            fuzzing_record_path = write_fuzzing_evidence_record(
                objective,
                evidence_dir,
                policy_decision=decision.summary,
                execution_mode="live_stub" if live else "dry_run",
                tool=result.tool,
                request_count=result.request_count,
                response_metadata=result.response_metadata,
            )
            register_artifact(
                manifest,
                evidence_dir,
                fuzzing_record_path,
                role="bounded_fuzzing_evidence_record",
                artifact_id="fuzzing-evidence-record",
                redaction_status="passed",
            )
            corpus_reference = result.response_metadata["fuzzing_plan"].get(
                "corpus_reference"
            )
            if isinstance(corpus_reference, dict):
                manifest.fuzzing_corpus_reference = str(
                    corpus_reference.get("alias", "")
                )
        if (
            result
            and objective.get("category") == "sbom_review"
            and isinstance(result.response_metadata.get("sbom_record"), dict)
        ):
            sbom_path = write_sbom_record(
                result.response_metadata["sbom_record"],
                evidence_dir,
            )
            register_artifact(
                manifest,
                evidence_dir,
                sbom_path,
                role="sbom_component_evidence",
                artifact_id="sbom-component-evidence",
                redaction_status="passed",
            )
            manifest.sbom_artifact = str(objective.get("artifact", ""))
        if (
            result
            and objective.get("category") == "crypto_controls"
            and isinstance(result.response_metadata.get("crypto_record"), dict)
        ):
            crypto_path = write_crypto_record(
                result.response_metadata["crypto_record"],
                evidence_dir,
            )
            register_artifact(
                manifest,
                evidence_dir,
                crypto_path,
                role="cryptographic_controls_evidence",
                artifact_id="crypto-controls-evidence",
                redaction_status="passed",
            )
            manifest.cryptographic_evidence = "crypto-evidence.json"
        write_manifest(manifest, evidence_dir)
        relative_evidence = str(evidence_dir.relative_to(root))
        if relative_evidence not in state.evidence_directories:
            state.evidence_directories.append(relative_evidence)
        state.request_counters["total"] += manifest.request_count
        if objective.get("category") == "bounded_fuzzing":
            for endpoint_alias in objective.get("endpoint_request_budgets", {}):
                state.endpoint_request_counters.setdefault(str(endpoint_alias), 0)
        budget.record(
            manifest.request_count,
            failed=outcome in {Verdict.FAIL, Verdict.STOPPED_BY_POLICY},
        )
        state.rate_limit_counters["current_minute"] = budget.current_minute_requests
        state.consecutive_failures = budget.consecutive_failures

        append_campaign_event(
            state,
            state_path,
            event_type="objective_result",
            iteration_id=iteration_id,
            objective_id=objective_id,
            module_name=str(objective.get("module", "")),
            policy_decision=decision.summary,
            outcome=str(outcome),
            evidence_directory=relative_evidence,
        )
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
            append_campaign_event(
                state,
                state_path,
                event_type="campaign_paused",
                iteration_id=iteration_id,
                objective_id=objective_id,
                module_name=str(objective.get("module", "")),
                outcome="paused_for_human_review",
                evidence_directory=relative_evidence,
                details={"phase": "pre_execution"},
            )
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
            append_campaign_event(
                state,
                state_path,
                event_type="campaign_paused",
                iteration_id=iteration_id,
                objective_id=objective_id,
                module_name=str(objective.get("module", "")),
                outcome="paused_for_human_review",
                evidence_directory=relative_evidence,
                details={"phase": "post_execution"},
            )
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
        append_campaign_event(
            state,
            state_path,
            event_type="campaign_completed",
            outcome="completed",
            details={"iterations": state.next_iteration - 1},
        )
    state.last_updated_time = utc_now()
    save_state(state, state_path)
    return state, state_path
