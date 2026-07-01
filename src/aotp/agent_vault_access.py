"""Authorized raw access to sensitive vault material."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evidence import utc_now
from .evidence_classifier import EvidenceClassification, parse_classification
from .roe import RulesOfEngagement
from .sensitive_vault import SensitiveVault, SensitiveVaultError
from .vault_handles import VaultHandle, parse_vault_handle


class AgentVaultAccessDenied(PermissionError):
    """Raised when an agent or tool cannot read raw vault material."""


@dataclass(frozen=True)
class VaultAccessContext:
    campaign_id: str
    target_alias: str
    identity: str
    purpose: str
    approved_classifications: frozenset[EvidenceClassification]
    approval_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.campaign_id or not self.target_alias or not self.identity or not self.purpose:
            raise AgentVaultAccessDenied("vault access context is incomplete")
        object.__setattr__(
            self,
            "approved_classifications",
            frozenset(parse_classification(item) for item in self.approved_classifications),
        )


@dataclass(frozen=True)
class VaultReadResult:
    handle: VaultHandle
    payload: bytes
    audit_record: dict[str, Any]


def read_vault_material(
    vault: SensitiveVault,
    handle: VaultHandle | str,
    *,
    context: VaultAccessContext,
    roe: RulesOfEngagement,
) -> VaultReadResult:
    parsed = parse_vault_handle(handle) if isinstance(handle, str) else handle
    reasons = _denial_reasons(parsed, context=context, roe=roe)
    if reasons:
        record = _audit_record(parsed, context=context, roe=roe, decision="denied", reasons=reasons)
        vault.append_access_log(record)
        raise AgentVaultAccessDenied("; ".join(reasons))
    metadata = vault.metadata(parsed)
    classification = parse_classification(metadata.classification)
    if classification not in context.approved_classifications:
        reasons = ("vault classification is not approved for this context",)
        record = _audit_record(parsed, context=context, roe=roe, decision="denied", reasons=reasons)
        vault.append_access_log(record)
        raise AgentVaultAccessDenied(reasons[0])
    if classification in {EvidenceClassification.POC_SENSITIVE, EvidenceClassification.RECIPIENT_ONLY}:
        if context.approval_reference is None or not context.approval_reference.strip():
            reasons = ("human approval reference is required for this vault classification",)
            record = _audit_record(parsed, context=context, roe=roe, decision="denied", reasons=reasons)
            vault.append_access_log(record)
            raise AgentVaultAccessDenied(reasons[0])
    try:
        payload = vault.read_raw(parsed)
    except SensitiveVaultError as exc:
        raise AgentVaultAccessDenied(str(exc)) from exc
    record = _audit_record(parsed, context=context, roe=roe, decision="allowed", reasons=())
    vault.append_access_log(record)
    return VaultReadResult(handle=parsed, payload=payload, audit_record=record)


def _denial_reasons(
    handle: VaultHandle,
    *,
    context: VaultAccessContext,
    roe: RulesOfEngagement,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if context.campaign_id != roe.campaign_id or handle.campaign_id != roe.campaign_id:
        reasons.append("vault access campaign does not match active ROE")
    if context.target_alias != roe.target_alias:
        reasons.append("vault access target does not match active ROE")
    if not roe.operator_approved:
        reasons.append("operator approval is required before vault access")
    return tuple(reasons)


def _audit_record(
    handle: VaultHandle,
    *,
    context: VaultAccessContext,
    roe: RulesOfEngagement,
    decision: str,
    reasons: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "timestamp_utc": utc_now(),
        "campaign_id": context.campaign_id,
        "active_campaign_id": roe.campaign_id,
        "target_alias": context.target_alias,
        "active_target_alias": roe.target_alias,
        "identity": context.identity,
        "purpose": context.purpose,
        "handle": handle.uri,
        "classification": handle.classification,
        "decision": decision,
        "reasons": list(reasons),
        "approval_reference": context.approval_reference,
    }
