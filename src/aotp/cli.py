"""AOTP command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from .bounded_fuzzing import build_corpus_reference, write_corpus_reference
from .campaign import load_campaign
from .campaign_loop import run_campaign
from .campaign_state import load_state, save_state
from .campaign_control import apply_review_decision, request_operator_stop
from .campaign_events import resolve_event_log, verify_state_event_log
from .config import ConfigError, load_yaml, validate_scope_shape
from .evidence import (
    EvidenceManifest,
    load_manifest,
    register_artifact,
    sha256_file,
    utc_now,
    verify_evidence_directory,
    write_manifest,
)
from .panel_evidence import write_panel_evidence_record
from .fuzzing_evidence import write_fuzzing_evidence_record
from .sbom_review import write_sbom_record
from .crypto_review import write_crypto_record
from .executor import execute
from .policy_gate import evaluate
from .reporter import generate_markdown
from .report_review import (
    PANEL_REVIEW_DECISION,
    PanelReportReviewDecision,
    manifest_requires_report_review,
    write_report_review_decision,
)
from .template_registry import parse_template_registry, verify_template_source
from .langgraph_orchestration import LangGraphCampaignOrchestrator
from .verifier import create_verification, write_verification
from .finding_candidate import create_candidate, load_candidate, write_candidate
from .finding_lifecycle import transition


from .sprint4_cli import dispatch_sprint4_command


ROOT = Path(__file__).resolve().parents[2]


def _yaml_files(directory: str) -> list[Path]:
    return sorted((ROOT / directory).glob("*.yaml"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aotp")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-config")
    validate.add_argument("--scope", required=True)
    validate.add_argument("--program-profile")
    validate.add_argument("--approval")
    validate.add_argument("--live", action="store_true")
    commands.add_parser("list-cases")
    commands.add_parser("list-modules")
    corpus_reference = commands.add_parser("fuzzing-corpus-reference")
    corpus_reference.add_argument("--corpus", required=True)
    corpus_reference.add_argument("--alias", required=True)
    corpus_reference.add_argument("--payload-class", required=True)
    corpus_reference.add_argument("--output", required=True)
    template_verify = commands.add_parser("template-source-verify")
    template_verify.add_argument("--registry", required=True)
    template_verify.add_argument("--source", required=True)
    policy = commands.add_parser("policy-check")
    policy.add_argument("--scope", required=True)
    policy.add_argument("--case", required=True)
    policy.add_argument("--program-profile")
    policy.add_argument("--approval")
    policy.add_argument("--live", action="store_true")
    policy.add_argument("--operator-approved", action="store_true")
    dry = commands.add_parser("dry-run")
    dry.add_argument("--scope", required=True)
    case = commands.add_parser("run-case")
    case.add_argument("--scope", required=True)
    case.add_argument("--case", required=True)
    mode = case.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--live", action="store_true")
    case.add_argument("--operator-approved", action="store_true")
    case.add_argument("--program-profile")
    case.add_argument("--approval")
    plan = commands.add_parser("campaign-plan")
    plan.add_argument("--scope", required=True)
    plan.add_argument("--campaign", required=True)
    run = commands.add_parser("campaign-run")
    run.add_argument("--scope", required=True)
    run.add_argument("--campaign", required=True)
    run.add_argument("--live", action="store_true")
    run.add_argument("--operator-approved", action="store_true")
    run.add_argument("--program-profile")
    run.add_argument("--approval")
    resume = commands.add_parser("campaign-resume")
    resume.add_argument("--state", required=True)
    resume.add_argument("--scope", required=True)
    resume.add_argument("--campaign", required=True)
    resume.add_argument("--review", required=True)
    resume.add_argument("--program-profile")
    resume.add_argument("--approval")
    resume.add_argument("--live", action="store_true")
    resume.add_argument("--operator-approved", action="store_true")
    stop = commands.add_parser("campaign-stop")
    stop.add_argument("--state", required=True)
    events_verify = commands.add_parser("campaign-events-verify")
    events_verify.add_argument("--state", required=True)
    verify = commands.add_parser("evidence-verify")
    verify.add_argument("--evidence", required=True)
    verdict = commands.add_parser("evidence-verdict")
    verdict.add_argument("--evidence", required=True)
    verdict.add_argument("--verdict", required=True)
    verdict.add_argument("--confidence", required=True)
    verdict.add_argument("--rationale", required=True)
    verdict.add_argument("--verifier", required=True)
    verdict.add_argument("--evidence-reference", action="append", default=[])
    finding_create = commands.add_parser("finding-create")
    finding_create.add_argument("--evidence", required=True)
    finding_create.add_argument("--verification", required=True)
    finding_create.add_argument("--finding-id", required=True)
    finding_create.add_argument("--title", required=True)
    finding_create.add_argument("--summary", required=True)
    finding_create.add_argument("--severity", default="unrated")
    finding_create.add_argument("--evidence-strength", default="weak")
    finding_create.add_argument("--report-review")
    finding_create.add_argument("--output", required=True)
    report_review = commands.add_parser("report-review-create")
    report_review.add_argument("--evidence", required=True)
    report_review.add_argument("--decision-id", required=True)
    report_review.add_argument("--reviewer", required=True)
    report_review.add_argument("--rationale", required=True)
    report_review.add_argument("--output", required=True)
    finding_transition = commands.add_parser("finding-transition")
    finding_transition.add_argument("--finding", required=True)
    finding_transition.add_argument("--state", required=True)
    finding_transition.add_argument("--reviewer", required=True)
    finding_transition.add_argument("--human-validated", action="store_true")
    report = commands.add_parser("report")
    report.add_argument("--evidence", required=True)
    report.add_argument("--findings")
    campaign_report = commands.add_parser("campaign-report")
    campaign_report.add_argument("--state", required=True)
    graph_run = commands.add_parser("campaign-graph-run")
    graph_run.add_argument("--scope", required=True)
    graph_run.add_argument("--campaign", required=True)
    graph_run.add_argument("--program-profile")
    graph_run.add_argument("--approval")
    graph_run.add_argument("--live", action="store_true")
    graph_run.add_argument("--operator-approved", action="store_true")
    graph_run.add_argument("--checkpoint-db")
    graph_resume = commands.add_parser("campaign-graph-resume")
    graph_resume.add_argument("--scope", required=True)
    graph_resume.add_argument("--campaign", required=True)
    graph_resume.add_argument("--review", required=True)
    graph_resume.add_argument("--program-profile")
    graph_resume.add_argument("--approval")
    graph_resume.add_argument("--live", action="store_true")
    graph_resume.add_argument("--operator-approved", action="store_true")
    graph_resume.add_argument("--checkpoint-db")
    return parser


def _load_scope(path: str) -> tuple[Path, dict]:
    loaded = load_yaml(path)
    validate_scope_shape(loaded.data)
    return loaded.path, loaded.data


def _load_optional(path: str | None) -> dict | None:
    return load_yaml(path).data if path else None


def _run_case(args: argparse.Namespace) -> int:
    scope_path, scope = _load_scope(args.scope)
    case = load_yaml(args.case).data
    if case.get("category") == "sbom_review" and isinstance(case.get("artifact"), str):
        candidates = [
            (scope_path.parent / case["artifact"]).resolve(),
            (scope_path.parent.parent / case["artifact"]).resolve(),
            (Path.cwd() / case["artifact"]).resolve(),
        ]
        artifact_path = next((path for path in candidates if path.is_file()), candidates[0])
        case["_resolved_artifact_path"] = str(artifact_path)
    profile = _load_optional(args.program_profile)
    approval = _load_optional(args.approval)
    decision = evaluate(
        scope,
        case,
        program_profile=profile,
        operator_approval=approval,
        scope_sha256=sha256_file(scope_path),
        live=args.live,
        operator_approved=args.operator_approved,
        workspace=Path.cwd(),
    )
    result = execute(case, live=args.live) if decision.allowed else None
    evidence_root = Path(scope["evidence"]["workspace"])
    if not evidence_root.is_absolute():
        evidence_root = Path.cwd() / evidence_root
    evidence_dir = evidence_root / "cases" / str(uuid.uuid4())
    manifest = EvidenceManifest(
        run_id=str(uuid.uuid4()),
        timestamp_utc=utc_now(),
        operator=str(scope.get("operator_alias", "operator")),
        sponsor_alias=scope["sponsor_alias"],
        target_alias=str(case.get("target_alias", "none")),
        authorization_reference=str(scope["authorization"].get("reference", "")),
        rules_of_engagement_reference=str(scope["rules_of_engagement"].get("reference", "")),
        confidentiality_reference=scope["authorization"].get("confidentiality", {}).get("reference"),
        case_id=str(case.get("id", "unknown")),
        tool=result.tool if result else "policy-gate",
        verifier_verdict=str(result.verdict if result else "stopped_by_policy"),
        confidence="not_assessed",
        module_name=str(case.get("module", "")),
        wstg_mapping=list(case.get("wstg_mapping", [])),
        artifact_mapping=list(case.get("evidence_mappings", [])),
        target_category=str(case.get("target_category", "placeholder")),
        execution_mode="live_stub" if args.live else "dry_run",
        policy_decision=decision.summary,
        request_count=result.request_count if result else 0,
        response_metadata=result.response_metadata if result else {"policy_reasons": list(decision.reasons)},
    )
    if (
        result
        and case.get("category") == "service_control_panel"
        and isinstance(result.response_metadata, dict)
        and isinstance(result.response_metadata.get("observation_plan"), dict)
    ):
        panel_record_path = write_panel_evidence_record(
            case,
            evidence_dir,
            policy_decision=decision.summary,
            execution_mode="live_stub" if args.live else "dry_run",
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
        and case.get("category") == "bounded_fuzzing"
        and isinstance(result.response_metadata, dict)
        and isinstance(result.response_metadata.get("fuzzing_plan"), dict)
    ):
        fuzzing_record_path = write_fuzzing_evidence_record(
            case,
            evidence_dir,
            policy_decision=decision.summary,
            execution_mode="live_stub" if args.live else "dry_run",
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
            manifest.fuzzing_corpus_reference = str(corpus_reference.get("alias", ""))
    if (
        result
        and case.get("category") == "sbom_review"
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
        manifest.sbom_artifact = str(case.get("artifact", ""))
    if (
        result
        and case.get("category") == "crypto_controls"
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
    path = write_manifest(manifest, evidence_dir)
    print(json.dumps({"allowed": decision.allowed, "decision": decision.summary, "evidence": str(path)}))
    return 0 if decision.allowed else 2


def main(argv: list[str] | None = None) -> int:
    sprint4_cli_result = dispatch_sprint4_command(argv)
    if sprint4_cli_result is not None:
        return sprint4_cli_result
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "validate-config":
            scope_path, scope = _load_scope(args.scope)
            decision = evaluate(
                scope,
                program_profile=_load_optional(args.program_profile),
                operator_approval=_load_optional(args.approval),
                scope_sha256=sha256_file(scope_path),
                live=args.live,
                workspace=Path.cwd(),
            )
            print(
                json.dumps(
                    {"valid": decision.allowed, "scope_id": scope["scope_id"], "decision": decision.summary}
                )
            )
            return 0 if decision.allowed else 2
        if args.command == "list-cases":
            for path in _yaml_files("cases"):
                print(path.name)
            return 0
        if args.command == "list-modules":
            for name in ("wstg_webapp", "service_control_panel", "bounded_fuzzing", "sbom_review", "crypto_controls"):
                print(name)
            return 0
        if args.command == "fuzzing-corpus-reference":
            reference = build_corpus_reference(
                args.corpus,
                alias=args.alias,
                payload_class=args.payload_class,
            )
            path = write_corpus_reference(reference, args.output)
            print(
                json.dumps(
                    {
                        "alias": reference["alias"],
                        "sha256": reference["sha256"],
                        "payload_count": reference["payload_count"],
                        "path": str(path),
                    }
                )
            )
            return 0
        if args.command == "template-source-verify":
            loaded = load_yaml(args.registry)
            sources = parse_template_registry(loaded.data)
            if args.source not in sources:
                raise ConfigError(f"template source is not registered: {args.source}")
            failures = verify_template_source(sources[args.source], loaded.path)
            print(
                json.dumps(
                    {
                        "valid": not failures,
                        "source": args.source,
                        "failures": failures,
                    },
                    indent=2,
                )
            )
            return 0 if not failures else 2
        if args.command == "policy-check":
            scope_path, scope = _load_scope(args.scope)
            case = load_yaml(args.case).data
            decision = evaluate(
                scope,
                case,
                program_profile=_load_optional(args.program_profile),
                operator_approval=_load_optional(args.approval),
                scope_sha256=sha256_file(scope_path),
                live=args.live,
                operator_approved=args.operator_approved,
                workspace=Path.cwd(),
            )
            print(
                json.dumps(
                    {
                        "allowed": decision.allowed,
                        "mode": "live" if args.live else "dry_run",
                        "scope_id": scope["scope_id"],
                        "case_id": case.get("id"),
                        "reasons": list(decision.reasons),
                    },
                    indent=2,
                )
            )
            return 0 if decision.allowed else 2
        if args.command == "dry-run":
            _, scope = _load_scope(args.scope)
            decision = evaluate(scope, workspace=Path.cwd())
            print(json.dumps({"mode": "dry_run", "allowed": decision.allowed, "decision": decision.summary}))
            return 0 if decision.allowed else 2
        if args.command == "run-case":
            return _run_case(args)
        if args.command == "campaign-plan":
            _, scope = _load_scope(args.scope)
            campaign = load_campaign(args.campaign).data
            decision = evaluate(scope, workspace=Path.cwd())
            print(json.dumps({"allowed": decision.allowed, "objectives": campaign["objectives"]}, indent=2))
            return 0 if decision.allowed else 2
        if args.command == "campaign-run":
            scope_path, scope = _load_scope(args.scope)
            campaign = load_campaign(args.campaign).data
            profile = _load_optional(args.program_profile)
            approval = _load_optional(args.approval)
            state, path = run_campaign(
                scope,
                scope_path,
                campaign,
                program_profile=profile,
                operator_approval=approval,
                live=args.live,
                operator_approved=args.operator_approved,
                workspace=Path.cwd(),
            )
            print(json.dumps({"status": state.current_status, "state": str(path)}))
            return 0 if state.current_status in {"completed", "paused_for_human_review"} else 2
        if args.command == "campaign-resume":
            state = load_state(args.state)
            apply_review_decision(state, args.state, load_yaml(args.review).data)
            if state.current_status != "ready_to_resume":
                print(json.dumps({"status": state.current_status, "state": args.state}))
                return 0
            scope_path, scope = _load_scope(args.scope)
            campaign = load_campaign(args.campaign).data
            state, path = run_campaign(
                scope,
                scope_path,
                campaign,
                program_profile=_load_optional(args.program_profile),
                operator_approval=_load_optional(args.approval),
                live=args.live,
                operator_approved=args.operator_approved,
                workspace=Path.cwd(),
                state=state,
                state_path=Path(args.state),
            )
            print(json.dumps({"status": state.current_status, "state": str(path)}))
            return 0 if state.current_status in {"completed", "paused_for_human_review"} else 2
        if args.command == "campaign-stop":
            state = load_state(args.state)
            request_operator_stop(state, args.state)
            print(json.dumps({"status": state.current_status, "state": args.state}))
            return 0
        if args.command == "campaign-events-verify":
            state = load_state(args.state)
            failures = verify_state_event_log(state, args.state)
            print(
                json.dumps(
                    {
                        "valid": not failures,
                        "event_log": str(resolve_event_log(state, args.state)),
                        "failures": failures,
                    },
                    indent=2,
                )
            )
            return 0 if not failures else 2
        if args.command == "evidence-verify":
            failures = verify_evidence_directory(args.evidence)
            print(json.dumps({"valid": not failures, "failures": failures}, indent=2))
            return 0 if not failures else 2
        if args.command == "evidence-verdict":
            manifest = load_manifest(args.evidence)
            result = create_verification(
                verdict=args.verdict,
                confidence=args.confidence,
                rationale=args.rationale,
                evidence_manifest_sha256=manifest.manifest_sha256 or "",
                evidence_references=args.evidence_reference,
                verifier=args.verifier,
            )
            path = write_verification(result, Path(args.evidence).parent / "verification.json")
            print(json.dumps({"verdict": result.verdict, "verification": str(path)}))
            return 0
        if args.command == "finding-create":
            candidate = create_candidate(
                args.evidence,
                args.verification,
                finding_id=args.finding_id,
                title=args.title,
                summary=args.summary,
                severity_candidate=args.severity,
                evidence_strength=args.evidence_strength,
                report_review_path=args.report_review,
            )
            path = write_candidate(candidate, args.output)
            print(json.dumps({"finding_id": candidate.finding_id, "state": candidate.state, "path": str(path)}))
            return 0
        if args.command == "report-review-create":
            manifest = load_manifest(args.evidence)
            if not manifest_requires_report_review(manifest):
                raise ValueError("evidence does not require a panel report review decision")
            decision = PanelReportReviewDecision(
                decision_id=args.decision_id,
                evidence_manifest_sha256=manifest.manifest_sha256 or "",
                reviewer_alias=args.reviewer,
                decision=PANEL_REVIEW_DECISION,
                decided_at_utc=utc_now(),
                rationale=args.rationale,
            )
            path = write_report_review_decision(decision, args.output)
            print(
                json.dumps(
                    {
                        "decision_id": decision.decision_id,
                        "reviewer": decision.reviewer_alias,
                        "evidence_manifest_sha256": decision.evidence_manifest_sha256,
                        "path": str(path),
                    }
                )
            )
            return 0
        if args.command == "finding-transition":
            candidate = load_candidate(args.finding)
            transition(
                candidate,
                args.state,
                reviewer=args.reviewer,
                human_validated=args.human_validated,
            )
            write_candidate(candidate, args.finding)
            print(json.dumps({"finding_id": candidate.finding_id, "state": candidate.state}))
            return 0
        if args.command == "report":
            print(generate_markdown(args.evidence, args.findings), end="")
            return 0
        if args.command == "campaign-report":
            state = load_state(args.state)
            roots = [Path.cwd() / item for item in state.evidence_directories]
            common = roots[0].parent if roots else Path("__missing__")
            print(generate_markdown(common), end="")
            return 0
        if args.command in {"campaign-graph-run", "campaign-graph-resume"}:
            scope_path, scope = _load_scope(args.scope)
            campaign = load_campaign(args.campaign).data
            checkpoint_db = Path(args.checkpoint_db) if args.checkpoint_db else None
            with LangGraphCampaignOrchestrator(
                scope=scope,
                scope_path=scope_path,
                campaign=campaign,
                workspace=Path.cwd(),
                program_profile=_load_optional(args.program_profile),
                operator_approval=_load_optional(args.approval),
                live=args.live,
                operator_approved=args.operator_approved,
                checkpoint_db=checkpoint_db,
            ) as orchestrator:
                if args.command == "campaign-graph-run":
                    snapshot = orchestrator.start()
                else:
                    snapshot = orchestrator.resume(load_yaml(args.review).data)
                print(
                    json.dumps(
                        {
                            "status": snapshot.get("status"),
                            "thread_id": orchestrator.thread_id,
                            "state": str(orchestrator.state_path),
                            "checkpoint_db": str(orchestrator.checkpoint_db),
                        }
                    )
                )
                return 0 if snapshot.get("status") in {
                    "completed",
                    "paused_for_human_review",
                } else 2
    except (ConfigError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
