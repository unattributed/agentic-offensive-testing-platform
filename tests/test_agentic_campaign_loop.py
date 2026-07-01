from __future__ import annotations

from dataclasses import dataclass

import pytest

from aotp.agent_tools.http_metadata import ToolExecutionResult
from aotp.agent_workspace import AgentCampaignWorkspace
from aotp.agentic_campaign_loop import AgenticCampaignError, run_agentic_campaign
from aotp.deep_agent.supervisor import SupervisorStatus
from aotp.model_proposal_gate import build_sprint14_policy
from aotp.model_proposals import ModelProposal


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
