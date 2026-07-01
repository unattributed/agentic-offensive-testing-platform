"""Three-iteration Ollama Deep Agent campaign loop for Sprint 14."""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .agent_tools.http_metadata import (
    NativeToolError,
    ToolExecutionResult,
    fetch_http_metadata,
    fetch_well_known_metadata,
)
from .agent_tools.tls_metadata import fetch_tls_metadata
from .agent_workspace import AgentCampaignWorkspace
from .deep_agent.bootstrap import OllamaBootstrap
from .deep_agent.supervisor import AOTPDeepAgentSupervisor, ProposalSupervisor
from .evidence import sha256_file, utc_now
from .evidence_summarizer import EvidenceSummary, summarize_tool_result
from .model_proposal_gate import (
    AgentCampaignPolicy,
    ProposalDecision,
    build_sprint14_policy,
    evaluate_model_proposal,
)
from .model_proposals import ModelProposal


class AgenticCampaignError(RuntimeError):
    """Raised when the Sprint 14 campaign cannot continue safely."""


@dataclass(frozen=True)
class AgenticCampaignResult:
    campaign_id: str
    run_id: str
    status: str
    workspace: str
    iterations: int
    request_count: int
    completed_objectives: tuple[str, ...]
    evidence_summaries: tuple[EvidenceSummary, ...]
    report_path: str

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_summaries"] = [
            summary.as_dict() for summary in self.evidence_summaries
        ]
        return value


ToolExecutor = Callable[[ModelProposal], ToolExecutionResult]


def execute_native_tool(proposal: ModelProposal) -> ToolExecutionResult:
    arguments = proposal.arguments_dict
    if proposal.tool_name == "http_metadata":
        return fetch_http_metadata(str(arguments["url"]))
    if proposal.tool_name == "tls_metadata":
        return fetch_tls_metadata(
            str(arguments["host"]),
            int(arguments["port"]),
            str(arguments["server_name"]),
        )
    if proposal.tool_name == "well_known_text":
        return fetch_well_known_metadata(str(arguments["base_url"]))
    raise AgenticCampaignError("proposal references an unregistered native tool")


def _write_denial(
    workspace: AgentCampaignWorkspace,
    *,
    iteration: int,
    proposal: ModelProposal,
    decision: ProposalDecision,
) -> None:
    workspace.write_json(
        "evidence",
        f"iteration-{iteration:02d}-denied",
        {
            "schema_version": "1.0",
            "timestamp_utc": utc_now(),
            "iteration": iteration,
            "proposal": proposal.model_dump(),
            "policy_decision": decision.summary,
            "executed": False,
        },
    )


def _due_diligence_report(
    policy: AgentCampaignPolicy,
    summaries: list[EvidenceSummary],
) -> str:
    lines = [
        "# Sprint 14 Agentic Campaign Due Diligence",
        "",
        f"- Campaign: `{policy.campaign_id}`",
        f"- Target alias: `{policy.target_alias}`",
        f"- Authorization reference: `{policy.authorization_reference}`",
        f"- Iterations completed: {len(summaries)}",
        f"- Requests used: {sum(item.request_count for item in summaries)}",
        "",
        "## Evidence",
        "",
    ]
    for summary in summaries:
        lines.extend(
            [
                f"### Iteration {summary.iteration}: {summary.objective_id}",
                "",
                f"- Tool: `{summary.tool_name}`",
                f"- Classification: `{summary.classification}`",
                f"- Artifact: `{summary.artifact_reference}`",
                f"- SHA256: `{summary.artifact_sha256}`",
                f"- Observations: `{json.dumps(summary.observations, sort_keys=True)}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Conclusion",
            "",
            "The campaign completed the approved metadata objectives. These observations do not "
            "establish a vulnerability. No credentials, state-changing actions, payload injection, "
            "or exploitation were used. Any finding requires separate evidence and review.",
            "",
        ]
    )
    return "\n".join(lines)


def run_agentic_campaign(
    *,
    supervisor: ProposalSupervisor,
    policy: AgentCampaignPolicy,
    workspace: AgentCampaignWorkspace,
    tool_executor: ToolExecutor = execute_native_tool,
) -> AgenticCampaignResult:
    supervisor_status = supervisor.start()
    workspace.write_json(
        "state",
        "supervisor",
        {
            "schema_version": "1.0",
            "timestamp_utc": utc_now(),
            "status": asdict(supervisor_status),
            "campaign_id": policy.campaign_id,
            "target_alias": policy.target_alias,
        },
    )
    completed: set[str] = set()
    summaries: list[EvidenceSummary] = []
    request_count = 0
    for iteration in range(1, policy.max_iterations + 1):
        remaining = policy.remaining(completed)
        if not remaining:
            raise AgenticCampaignError("campaign exhausted objectives before iteration limit")
        try:
            proposal = supervisor.propose(
                target_alias=policy.target_alias,
                remaining=remaining,
                evidence_summaries=[summary.as_dict() for summary in summaries],
            )
        except Exception as exc:
            workspace.write_json(
                "evidence",
                f"iteration-{iteration:02d}-model-failed",
                {
                    "schema_version": "1.0",
                    "timestamp_utc": utc_now(),
                    "iteration": iteration,
                    "executed": False,
                    "result": "Deep Agent did not return a valid structured proposal",
                },
            )
            raise AgenticCampaignError(
                "Deep Agent did not return a valid structured proposal"
            ) from exc
        decision = evaluate_model_proposal(proposal, policy, completed=completed)
        if not decision.allowed:
            _write_denial(
                workspace,
                iteration=iteration,
                proposal=proposal,
                decision=decision,
            )
            raise AgenticCampaignError(
                "model proposal denied by campaign policy: " + decision.summary
            )
        predicted_requests = 2 if proposal.tool_name == "well_known_text" else 1
        if request_count + predicted_requests > policy.max_requests:
            budget_decision = ProposalDecision(False, ("campaign request budget exceeded",))
            _write_denial(
                workspace,
                iteration=iteration,
                proposal=proposal,
                decision=budget_decision,
            )
            raise AgenticCampaignError("campaign request budget exceeded")
        try:
            result = tool_executor(proposal)
        except (KeyError, TypeError, ValueError, NativeToolError) as exc:
            workspace.write_json(
                "evidence",
                f"iteration-{iteration:02d}-failed",
                {
                    "schema_version": "1.0",
                    "timestamp_utc": utc_now(),
                    "iteration": iteration,
                    "proposal": proposal.model_dump(),
                    "policy_decision": "allowed",
                    "executed": True,
                    "result": "bounded native tool failed",
                },
            )
            raise AgenticCampaignError("bounded native tool failed") from exc
        if result.tool_name != proposal.tool_name:
            raise AgenticCampaignError("native tool result identity does not match proposal")
        if result.request_count != predicted_requests:
            raise AgenticCampaignError("native tool request count violates its registered contract")
        request_count += result.request_count
        artifact = workspace.write_json(
            "evidence",
            f"iteration-{iteration:02d}-{proposal.objective_id}",
            {
                "schema_version": "1.0",
                "timestamp_utc": utc_now(),
                "campaign_id": policy.campaign_id,
                "authorization_reference": policy.authorization_reference,
                "iteration": iteration,
                "proposal": proposal.model_dump(),
                "policy_decision": decision.summary,
                "request_count": result.request_count,
                "classification": "public",
                "result": result.result,
            },
        )
        relative_artifact = str(artifact.relative_to(workspace.path))
        summary = summarize_tool_result(
            iteration=iteration,
            objective_id=proposal.objective_id,
            result=result,
            artifact_reference=relative_artifact,
            artifact_sha256=sha256_file(artifact),
        )
        summaries.append(summary)
        completed.add(proposal.objective_id)
        workspace.write_json(
            "state",
            "campaign",
            {
                "schema_version": "1.0",
                "timestamp_utc": utc_now(),
                "campaign_id": policy.campaign_id,
                "status": "running",
                "iterations": iteration,
                "request_count": request_count,
                "completed_objectives": sorted(completed),
                "evidence_summaries": [item.as_dict() for item in summaries],
            },
        )
    if len(completed) != 3 or request_count != 4:
        raise AgenticCampaignError("Sprint 14 campaign did not complete its bounded contract")
    report = workspace.write_text(
        "reports",
        "due-diligence",
        _due_diligence_report(policy, summaries),
    )
    result = AgenticCampaignResult(
        campaign_id=policy.campaign_id,
        run_id=workspace.run_id,
        status="completed",
        workspace=str(workspace.path),
        iterations=len(summaries),
        request_count=request_count,
        completed_objectives=tuple(sorted(completed)),
        evidence_summaries=tuple(summaries),
        report_path=str(report),
    )
    workspace.write_json("state", "campaign-result", result.as_dict())
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m aotp.agentic_campaign_loop")
    parser.add_argument("--target", required=True, help="Authorized HTTPS origin")
    parser.add_argument("--program", required=True, help="Safe private program alias")
    parser.add_argument("--target-alias", required=True)
    parser.add_argument("--authorization-reference", required=True)
    parser.add_argument("--operator-approved", action="store_true")
    parser.add_argument("--model", default="gemma4:latest")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--workspace-root", default=".aotp/campaigns")
    parser.add_argument("--run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    run_id = args.run_id or uuid.uuid4().hex
    policy = build_sprint14_policy(
        campaign_id=f"sprint14-{run_id}",
        program_alias=args.program,
        target_alias=args.target_alias,
        base_url=args.target,
        authorization_reference=args.authorization_reference,
        operator_approved=args.operator_approved,
    )
    workspace = AgentCampaignWorkspace.create(
        args.workspace_root,
        program_alias=args.program,
        run_id=run_id,
    )
    supervisor = AOTPDeepAgentSupervisor(
        OllamaBootstrap(base_url=args.ollama_url, model=args.model)
    )
    result = run_agentic_campaign(
        supervisor=supervisor,
        policy=policy,
        workspace=workspace,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
