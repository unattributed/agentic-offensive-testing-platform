"""Approval gates for vault export, report inclusion, and campaign handoff."""

from __future__ import annotations

from dataclasses import dataclass

from .evidence_classifier import EvidenceClassification, parse_classification


class ReportExportPolicyError(PermissionError):
    """Raised when a sensitive export or report inclusion is not approved."""


@dataclass(frozen=True)
class SensitiveExportApproval:
    approval_id: str
    operator_alias: str
    campaign_id: str
    action: str
    approved: bool
    reason: str

    def validate_for(self, *, campaign_id: str, action: str) -> None:
        if not self.approved:
            raise ReportExportPolicyError("sensitive export approval is not approved")
        if self.campaign_id != campaign_id:
            raise ReportExportPolicyError("sensitive export approval campaign mismatch")
        if self.action != action:
            raise ReportExportPolicyError("sensitive export approval action mismatch")
        if not self.approval_id or not self.operator_alias or not self.reason:
            raise ReportExportPolicyError("sensitive export approval is incomplete")


def normal_report_may_reference(classification: str | EvidenceClassification) -> bool:
    parsed = parse_classification(classification)
    return parsed in {EvidenceClassification.PUBLIC, EvidenceClassification.RESTRICTED}


def require_report_inclusion_approval(
    *,
    campaign_id: str,
    classification: str | EvidenceClassification,
    approval: SensitiveExportApproval | None,
) -> None:
    if normal_report_may_reference(classification):
        return
    if approval is None:
        raise ReportExportPolicyError("sensitive report inclusion requires human approval")
    approval.validate_for(campaign_id=campaign_id, action="report_inclusion")


def require_annex_export_approval(
    *,
    campaign_id: str,
    approval: SensitiveExportApproval | None,
) -> None:
    if approval is None:
        raise ReportExportPolicyError("sensitive annex export requires human approval")
    approval.validate_for(campaign_id=campaign_id, action="annex_export")


def require_campaign_handoff_approval(
    *,
    campaign_id: str,
    approval: SensitiveExportApproval | None,
) -> None:
    if approval is None:
        raise ReportExportPolicyError("campaign handoff requires human approval")
    approval.validate_for(campaign_id=campaign_id, action="campaign_handoff")
