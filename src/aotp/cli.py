"""AOTP command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from .campaign import load_campaign
from .campaign_loop import run_campaign
from .campaign_state import load_state, save_state
from .campaign_control import apply_review_decision, request_operator_stop
from .config import ConfigError, load_yaml, validate_scope_shape
from .evidence import EvidenceManifest, sha256_file, utc_now, verify_evidence_directory, write_manifest
from .executor import execute
from .policy_gate import evaluate
from .reporter import generate_markdown
from .template_registry import parse_template_registry, verify_template_source


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
    verify = commands.add_parser("evidence-verify")
    verify.add_argument("--evidence", required=True)
    report = commands.add_parser("report")
    report.add_argument("--evidence", required=True)
    campaign_report = commands.add_parser("campaign-report")
    campaign_report.add_argument("--state", required=True)
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
        target_category=str(case.get("target_category", "placeholder")),
        execution_mode="live_stub" if args.live else "dry_run",
        policy_decision=decision.summary,
        request_count=result.request_count if result else 0,
        response_metadata=result.response_metadata if result else {"policy_reasons": list(decision.reasons)},
    )
    path = write_manifest(manifest, evidence_dir)
    print(json.dumps({"allowed": decision.allowed, "decision": decision.summary, "evidence": str(path)}))
    return 0 if decision.allowed else 2


def main(argv: list[str] | None = None) -> int:
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
        if args.command == "evidence-verify":
            failures = verify_evidence_directory(args.evidence)
            print(json.dumps({"valid": not failures, "failures": failures}, indent=2))
            return 0 if not failures else 2
        if args.command == "report":
            print(generate_markdown(args.evidence), end="")
            return 0
        if args.command == "campaign-report":
            state = load_state(args.state)
            roots = [Path.cwd() / item for item in state.evidence_directories]
            common = roots[0].parent if roots else Path("__missing__")
            print(generate_markdown(common), end="")
            return 0
    except (ConfigError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
