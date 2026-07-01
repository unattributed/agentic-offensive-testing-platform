from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet

from aotp.report_export_policy import (
    ReportExportPolicyError,
    SensitiveExportApproval,
    normal_report_may_reference,
    require_campaign_handoff_approval,
    require_report_inclusion_approval,
)
from aotp.sensitive_annex import export_sensitive_annex
from aotp.sensitive_vault import SensitiveVault


def _approval(action="annex_export", campaign_id="campaign-1"):
    return SensitiveExportApproval(
        approval_id="approval-1",
        operator_alias="operator",
        campaign_id=campaign_id,
        action=action,
        approved=True,
        reason="authorized recipient package",
    )


def test_sensitive_annex_export_requires_approval_and_stays_separate(tmp_path):
    vault = SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())
    raw = "password=abcdefghi123456"
    handle = vault.store(raw, artifact_kind="password", purpose="authorized proof")
    result = export_sensitive_annex(
        vault=vault,
        handles=(handle,),
        output_dir=tmp_path / "annex",
        approval=_approval(),
        recipient_alias="triager",
    )
    assert result.encrypted_annex_path.is_file()
    assert result.manifest_path.is_file()
    assert raw not in result.encrypted_annex_path.read_text(encoding="utf-8", errors="ignore")
    assert raw not in result.manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["encrypted_annex_path"] == result.encrypted_annex_path.name
    assert manifest["annex_key_delivery"] == "manual_out_of_band_not_stored_in_manifest"


def test_sensitive_annex_export_denies_missing_or_wrong_approval(tmp_path):
    vault = SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())
    handle = vault.store("password=abcdefghi123456", artifact_kind="password", purpose="authorized")
    with pytest.raises(ReportExportPolicyError, match="action"):
        export_sensitive_annex(
            vault=vault,
            handles=(handle,),
            output_dir=tmp_path / "annex",
            approval=_approval(action="report_inclusion"),
            recipient_alias="triager",
        )


def test_report_export_policy_gates_sensitive_inclusion_and_handoff():
    assert normal_report_may_reference("restricted") is True
    assert normal_report_may_reference("secret") is False
    with pytest.raises(ReportExportPolicyError, match="approval"):
        require_report_inclusion_approval(
            campaign_id="campaign-1",
            classification="secret",
            approval=None,
        )
    require_report_inclusion_approval(
        campaign_id="campaign-1",
        classification="secret",
        approval=_approval(action="report_inclusion"),
    )
    with pytest.raises(ReportExportPolicyError, match="requires human approval"):
        require_campaign_handoff_approval(campaign_id="campaign-1", approval=None)
