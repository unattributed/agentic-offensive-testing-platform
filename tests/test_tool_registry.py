import json

import pytest

from aotp.agent_workspace import AgentCampaignWorkspace
from aotp.request_budget import RequestBudget
from aotp.roe import RulesOfEngagement
from aotp.tool_registry import (
    NativeToolCall,
    NativeToolRegistry,
    NativeToolSpec,
    ToolArgument,
    ToolExecutionDenied,
    build_default_native_tool_registry,
)
from aotp.tool_risk_tiers import ToolRiskTier


def _roe(*, tools=("http_metadata",), tiers=(ToolRiskTier.PASSIVE_METADATA,), hosts=("example.com",), ports=(443,), approvals=None):
    return RulesOfEngagement(
        campaign_id="campaign-1",
        target_alias="target-1",
        authorization_reference="auth-1",
        operator_approved=True,
        allowed_tool_names=frozenset(tools),
        allowed_risk_tiers=frozenset(tiers),
        allowed_hosts=frozenset(hosts),
        allowed_ports=frozenset(ports),
        approval_references=approvals or {},
    )


def test_default_registry_contains_sprint15_tools():
    registry = build_default_native_tool_registry()
    names = {spec.name for spec in registry.list_specs()}
    assert {
        "campaign_shell",
        "http_metadata",
        "nmap_governed",
        "playwright_passive_metadata",
        "tls_metadata",
        "well_known_text",
        "zap_passive_baseline",
    }.issubset(names)


def test_unregistered_tool_is_denied():
    registry = build_default_native_tool_registry()
    call = NativeToolCall(
        campaign_id="campaign-1",
        target_alias="target-1",
        tool_name="shell",
        arguments={},
    )
    decision = registry.evaluate(call, _roe(), RequestBudget(max_requests=1))
    assert not decision.allowed
    assert decision.reasons == ("native tool is not registered",)


def test_registered_tool_requires_exact_typed_arguments():
    registry = build_default_native_tool_registry()
    call = NativeToolCall(
        campaign_id="campaign-1",
        target_alias="target-1",
        tool_name="http_metadata",
        arguments={"url": "https://example.com/", "extra": "denied"},
    )
    decision = registry.evaluate(call, _roe(), RequestBudget(max_requests=1))
    assert not decision.allowed
    assert "unknown tool arguments: extra" in decision.reasons


def test_roe_and_budget_are_checked_before_execution():
    executed = {"value": False}

    def executor(_arguments):
        executed["value"] = True
        return {"ok": True}

    registry = NativeToolRegistry(
        (
            NativeToolSpec(
                name="http_metadata",
                description="test",
                risk_tier=ToolRiskTier.PASSIVE_METADATA,
                arguments=(ToolArgument("url", str),),
                request_cost=1,
                evidence_classification="public",
                executor=executor,
            ),
        )
    )
    call = NativeToolCall(
        campaign_id="campaign-1",
        target_alias="target-1",
        tool_name="http_metadata",
        arguments={"url": "https://example.com/"},
    )
    with pytest.raises(ToolExecutionDenied):
        registry.execute(call, _roe(tools=("campaign_shell",)), RequestBudget(max_requests=1))
    assert not executed["value"]


def test_denied_tool_call_is_written_as_campaign_evidence(tmp_path):
    workspace = AgentCampaignWorkspace.create(tmp_path / "workspace", program_alias="program", run_id="run-1")
    registry = build_default_native_tool_registry()
    call = NativeToolCall(
        campaign_id="campaign-1",
        target_alias="target-1",
        tool_name="http_metadata",
        arguments={"url": "https://out.example/"},
    )
    with pytest.raises(ToolExecutionDenied):
        registry.execute(call, _roe(), RequestBudget(max_requests=1), workspace=workspace)
    evidence_files = sorted(workspace.evidence.glob("denied-http_metadata-*.json"))
    assert len(evidence_files) == 1
    record = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert record["allowed"] is False
    assert record["executed"] is False
    assert record["denial_reasons"] == ["URL host is outside ROE scope"]


def test_service_fingerprint_requires_explicit_human_approval():
    registry = build_default_native_tool_registry()
    call = NativeToolCall(
        campaign_id="campaign-1",
        target_alias="target-1",
        tool_name="nmap_governed",
        arguments={"host": "example.com", "port": 443, "service_name": "https"},
    )
    roe = _roe(
        tools=("nmap_governed",),
        tiers=(ToolRiskTier.SERVICE_FINGERPRINT,),
        hosts=("example.com",),
        ports=(443,),
    )
    denied = registry.evaluate(call, roe, RequestBudget(max_requests=1))
    assert not denied.allowed
    assert "required human approval reference is missing" in denied.reasons
    approved = _roe(
        tools=("nmap_governed",),
        tiers=(ToolRiskTier.SERVICE_FINGERPRINT,),
        hosts=("example.com",),
        ports=(443,),
        approvals={"service_fingerprint": "operator-approved-1"},
    )
    allowed = registry.evaluate(call, approved, RequestBudget(max_requests=1))
    assert allowed.allowed


def test_denied_tool_evidence_redacts_credential_like_arguments(tmp_path):
    workspace = AgentCampaignWorkspace.create(tmp_path / "workspace", program_alias="program", run_id="run-1")
    registry = build_default_native_tool_registry()
    call = NativeToolCall(
        campaign_id="campaign-1",
        target_alias="target-1",
        tool_name="http_metadata",
        arguments={"url": "https://user:pass@example.com/", "token": "secret-value"},
    )
    with pytest.raises(ToolExecutionDenied):
        registry.execute(call, _roe(), RequestBudget(max_requests=1), workspace=workspace)
    evidence_files = sorted(workspace.evidence.glob("denied-http_metadata-*.json"))
    record = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert record["proposal_arguments"]["url"] == "<redacted-url-credentials>"
    assert record["proposal_arguments"]["token"] == "<redacted>"
