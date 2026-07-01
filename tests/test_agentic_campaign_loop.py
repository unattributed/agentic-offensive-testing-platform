from __future__ import annotations

from dataclasses import dataclass

import pytest

from aotp.agent_tools.http_metadata import ToolExecutionResult
from aotp.agent_workspace import AgentCampaignWorkspace
from aotp.agentic_campaign_loop import AgenticCampaignError, run_agentic_campaign
from aotp.deep_agent.supervisor import SupervisorStatus
from aotp.model_proposal_gate import build_sprint14_policy
from aotp.model_proposals import ModelProposal
from aotp.tool_registry import NativeToolRegistry, NativeToolSpec, ToolArgument
from aotp.tool_risk_tiers import ToolRiskTier


@dataclass
class ScriptedSupervisor:
    mutate_second_target: bool = False

    def __post_init__(self):
        self.calls = []

    def start(self):
        return SupervisorStatus(
            framework="test-deep-agent",
            model="local-test-model",
            model_digest="a" * 64,
            subagents=("planner", "analyst", "reporter"),
            started=True,
        )

    def propose(self, *, target_alias, remaining, evidence_summaries):
        self.calls.append(list(evidence_summaries))
        objective = remaining[0]
        if len(self.calls) > 1:
            assert evidence_summaries
            assert evidence_summaries[-1]["artifact_sha256"]
        return ModelProposal(
            objective_id=objective.objective_id,
            tool_name=objective.tool_name,
            target_alias=(
                "outside-target"
                if self.mutate_second_target and len(self.calls) == 2
                else target_alias
            ),
            arguments=objective.arguments,
            rationale="Use the approved next objective.",
        )


def _policy():
    return build_sprint14_policy(
        campaign_id="sprint14-test",
        program_alias="owned-program",
        target_alias="owned-mail",
        base_url="https://mail.example.invalid/",
        authorization_reference="owner-approved-sprint14",
        operator_approved=True,
    )


def _executor(proposal):
    if proposal.tool_name == "http_metadata":
        return ToolExecutionResult(
            "http_metadata",
            1,
            {
                "status": 200,
                "headers": {"content-type": "text/html"},
                "body_bytes_observed": 10,
                "body_sha256": "1" * 64,
                "body_truncated": False,
            },
        )
    if proposal.tool_name == "tls_metadata":
        return ToolExecutionResult(
            "tls_metadata",
            1,
            {
                "tls_version": "TLSv1.3",
                "cipher": "TLS_AES_256_GCM_SHA384",
                "certificate_sha256": "2" * 64,
                "subject": {"commonName": "mail.example.invalid"},
                "issuer": {"commonName": "test-ca"},
                "not_before": "test",
                "not_after": "test",
                "subject_alt_names": ["mail.example.invalid"],
            },
        )
    return ToolExecutionResult(
        "well_known_text",
        2,
        {
            "checks": [
                {
                    "url": "https://mail.example.invalid/robots.txt",
                    "status": 404,
                    "headers": {"content-type": "text/plain"},
                    "body_sha256": "3" * 64,
                    "body_truncated": False,
                },
                {
                    "url": "https://mail.example.invalid/.well-known/security.txt",
                    "status": 200,
                    "headers": {"content-type": "text/plain"},
                    "body_sha256": "4" * 64,
                    "body_truncated": False,
                },
            ]
        },
    )


def test_three_iteration_loop_hashes_evidence_and_writes_due_diligence(tmp_path):
    workspace = AgentCampaignWorkspace.create(
        tmp_path / ".aotp" / "campaigns",
        program_alias="owned-program",
        run_id="run-001",
    )
    supervisor = ScriptedSupervisor()
    result = run_agentic_campaign(
        supervisor=supervisor,
        policy=_policy(),
        workspace=workspace,
        tool_executor=_executor,
    )
    assert result.status == "completed"
    assert result.iterations == 3
    assert result.request_count == 4
    assert len(result.evidence_summaries) == 3
    assert len(list(workspace.evidence.glob("iteration-*.json"))) == 3
    assert all(len(item.artifact_sha256) == 64 for item in result.evidence_summaries)
    report = (workspace.reports / "due-diligence.md").read_text()
    assert "do not establish a vulnerability" in report
    assert len(supervisor.calls[0]) == 0
    assert len(supervisor.calls[1]) == 1
    assert len(supervisor.calls[2]) == 2


def test_denied_second_proposal_is_evidence_and_never_executes(tmp_path):
    workspace = AgentCampaignWorkspace.create(
        tmp_path / "campaigns",
        program_alias="owned-program",
        run_id="run-001",
    )
    calls = []

    def executor(proposal):
        calls.append(proposal.objective_id)
        return _executor(proposal)

    with pytest.raises(AgenticCampaignError, match="denied"):
        run_agentic_campaign(
            supervisor=ScriptedSupervisor(mutate_second_target=True),
            policy=_policy(),
            workspace=workspace,
            tool_executor=executor,
        )
    assert calls == ["http-root-metadata"]
    denial = workspace.evidence / "iteration-02-denied.json"
    assert denial.is_file()
    assert "outside the active campaign" in denial.read_text()


def _registry_executor_for(tool_name, request_count, result):
    def executor(_arguments):
        return result

    if tool_name == "http_metadata":
        arguments = (ToolArgument("url", str),)
    elif tool_name == "tls_metadata":
        arguments = (ToolArgument("host", str), ToolArgument("port", int), ToolArgument("server_name", str))
    else:
        arguments = (ToolArgument("base_url", str),)
    return NativeToolSpec(
        name=tool_name,
        description="test registry executor",
        risk_tier=ToolRiskTier.PASSIVE_METADATA,
        arguments=arguments,
        request_cost=request_count,
        evidence_classification="public",
        executor=executor,
    )


def test_campaign_loop_routes_default_execution_through_registry(tmp_path):
    workspace = AgentCampaignWorkspace.create(
        tmp_path / "campaigns",
        program_alias="owned-program",
        run_id="run-001",
    )
    registry = NativeToolRegistry(
        (
            _registry_executor_for(
                "http_metadata",
                1,
                {
                    "status": 200,
                    "headers": {"content-type": "text/html"},
                    "body_bytes_observed": 10,
                    "body_sha256": "1" * 64,
                    "body_truncated": False,
                },
            ),
            _registry_executor_for(
                "tls_metadata",
                1,
                {
                    "tls_version": "TLSv1.3",
                    "cipher": "TLS_AES_256_GCM_SHA384",
                    "certificate_sha256": "2" * 64,
                    "subject": {"commonName": "mail.example.invalid"},
                    "issuer": {"commonName": "test-ca"},
                    "not_before": "test",
                    "not_after": "test",
                    "subject_alt_names": ["mail.example.invalid"],
                },
            ),
            _registry_executor_for(
                "well_known_text",
                2,
                {
                    "checks": [
                        {
                            "url": "https://mail.example.invalid/robots.txt",
                            "status": 404,
                            "headers": {"content-type": "text/plain"},
                            "body_sha256": "3" * 64,
                            "body_truncated": False,
                        },
                        {
                            "url": "https://mail.example.invalid/.well-known/security.txt",
                            "status": 200,
                            "headers": {"content-type": "text/plain"},
                            "body_sha256": "4" * 64,
                            "body_truncated": False,
                        },
                    ]
                },
            ),
        )
    )
    result = run_agentic_campaign(
        supervisor=ScriptedSupervisor(),
        policy=_policy(),
        workspace=workspace,
        native_tool_registry=registry,
    )
    assert result.status == "completed"
    assert result.request_count == 4
    assert len(list(workspace.evidence.glob("executed-*.json"))) == 3
