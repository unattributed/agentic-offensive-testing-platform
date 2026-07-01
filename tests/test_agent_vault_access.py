from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet

from aotp.agent_vault_access import AgentVaultAccessDenied, VaultAccessContext, read_vault_material
from aotp.evidence_classifier import EvidenceClassification
from aotp.roe import RulesOfEngagement
from aotp.sensitive_vault import SensitiveVault
from aotp.tool_risk_tiers import ToolRiskTier


def _roe(campaign_id="campaign-1", target_alias="target-1"):
    return RulesOfEngagement(
        campaign_id=campaign_id,
        target_alias=target_alias,
        authorization_reference="auth-1",
        operator_approved=True,
        allowed_tool_names=frozenset({"http_metadata"}),
        allowed_risk_tiers=frozenset({ToolRiskTier.PASSIVE_METADATA}),
        allowed_hosts=frozenset({"example.invalid"}),
    )


def _context(*, campaign_id="campaign-1", approvals=None, approval_reference=None):
    return VaultAccessContext(
        campaign_id=campaign_id,
        target_alias="target-1",
        identity="agent:analyst",
        purpose="compare proof across campaign iterations",
        approved_classifications=frozenset(approvals or {EvidenceClassification.SECRET}),
        approval_reference=approval_reference,
    )


def test_raw_vault_read_requires_active_campaign_and_is_audited(tmp_path):
    vault = SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())
    raw = "password=abcdefghi123456"
    handle = vault.store(raw, artifact_kind="password", purpose="authorized credential proof")
    result = read_vault_material(vault, handle, context=_context(), roe=_roe())
    assert result.payload.decode() == raw
    log = vault.access_log_path.read_text(encoding="utf-8")
    assert raw not in log
    record = json.loads(log.splitlines()[0])
    assert record["decision"] == "allowed"
    assert record["handle"] == handle.uri
    assert record["identity"] == "agent:analyst"


def test_raw_vault_read_denies_outside_active_campaign_and_logs_denial(tmp_path):
    vault = SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())
    handle = vault.store("password=abcdefghi123456", artifact_kind="password", purpose="authorized")
    with pytest.raises(AgentVaultAccessDenied, match="campaign"):
        read_vault_material(vault, handle, context=_context(campaign_id="other"), roe=_roe())
    records = [json.loads(line) for line in vault.access_log_path.read_text().splitlines()]
    assert records[-1]["decision"] == "denied"


def test_poc_sensitive_read_requires_human_approval_reference(tmp_path):
    vault = SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())
    handle = vault.store(
        "poc replay steps",
        classification="poc_sensitive",
        artifact_kind="proof",
        purpose="reproducible proof",
    )
    approvals = {EvidenceClassification.POC_SENSITIVE}
    with pytest.raises(AgentVaultAccessDenied, match="human approval"):
        read_vault_material(vault, handle, context=_context(approvals=approvals), roe=_roe())
    approved = _context(approvals=approvals, approval_reference="approval-1")
    assert read_vault_material(vault, handle, context=approved, roe=_roe()).payload
