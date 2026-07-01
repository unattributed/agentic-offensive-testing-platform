from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from aotp.agent_vault_access import VaultAccessContext
from aotp.evidence_classifier import EvidenceClassification
from aotp.roe import RulesOfEngagement
from aotp.secret_bearing_tools import (
    SecretBearingToolError,
    assert_no_secret_in_process_surface,
    run_secret_bearing_tool,
)
from aotp.sensitive_vault import SensitiveVault
from aotp.tool_risk_tiers import ToolRiskTier


def _roe():
    return RulesOfEngagement(
        campaign_id="campaign-1",
        target_alias="target-1",
        authorization_reference="auth-1",
        operator_approved=True,
        allowed_tool_names=frozenset({"http_metadata"}),
        allowed_risk_tiers=frozenset({ToolRiskTier.PASSIVE_METADATA}),
        allowed_hosts=frozenset({"example.invalid"}),
    )


def _context():
    return VaultAccessContext(
        campaign_id="campaign-1",
        target_alias="target-1",
        identity="tool:synthetic",
        purpose="in-memory validation",
        approved_classifications=frozenset({EvidenceClassification.SECRET}),
    )


def test_secret_bearing_tool_uses_material_in_memory_without_argv_or_log_leakage(tmp_path):
    vault = SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())
    secret = b"password=abcdefghi123456"
    handle = vault.store(secret, artifact_kind="password", purpose="synthetic")
    result = run_secret_bearing_tool(
        tool_name="synthetic-secret-check",
        vault=vault,
        handle=handle,
        context=_context(),
        roe=_roe(),
        argv_template=("synthetic-tool", "--handle", handle.uri),
        handler=lambda payload: {"payload_sha256_prefix": payload.hex()[:8], "raw_used": False},
    )
    assert result.handle == handle.uri
    assert_no_secret_in_process_surface(result, secret)
    assert "raw_material=not_logged" in result.log_lines


def test_secret_bearing_tool_denies_secret_argv_template(tmp_path):
    vault = SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())
    handle = vault.store("password=abcdefghi123456", artifact_kind="password", purpose="synthetic")
    with pytest.raises(SecretBearingToolError, match="argv"):
        run_secret_bearing_tool(
            tool_name="bad-tool",
            vault=vault,
            handle=handle,
            context=_context(),
            roe=_roe(),
            argv_template=("bad-tool", "{secret}"),
            handler=lambda payload: {"ok": True},
        )


def test_secret_bearing_tool_blocks_sensitive_result(tmp_path):
    vault = SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())
    handle = vault.store("password=abcdefghi123456", artifact_kind="password", purpose="synthetic")
    with pytest.raises(Exception, match="normal evidence"):
        run_secret_bearing_tool(
            tool_name="bad-result",
            vault=vault,
            handle=handle,
            context=_context(),
            roe=_roe(),
            argv_template=("bad-result", "--handle", handle.uri),
            handler=lambda payload: {"secret_result": "api" + "_key=abcdefghi123456"},
        )
