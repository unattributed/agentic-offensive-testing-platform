"""Deferred OWASP ZAP passive review and limited spider contract."""

from __future__ import annotations

from ..adapter_contract import AdapterContract

CONTRACT = AdapterContract(
    adapter_id="zap",
    display_name="OWASP ZAP passive and limited spider contract",
    source_reference="https://www.zaproxy.org/docs/automate/automation-framework/",
    supported_capabilities=(
        "passive_scan_placeholder",
        "limited_spider_placeholder",
    ),
    required_approvals=(
        "explicit_private_scope",
        "policy_gate_approval",
        "future_live_readiness_approval",
        "explicit_spider_approval",
    ),
    required_scope_fields=(
        "target_alias",
        "allowed_urls",
        "rate_limits",
        "spider_limits",
        "evidence_rules",
    ),
    required_evidence_handling=(
        "redaction_required",
        "local_only",
        "artifact_hash_required",
        "passive_metadata_only_by_default",
    ),
    denied_actions=(
        "active_scan_by_default",
        "active_scan_without_approval",
        "destructive_payloads",
        "live_use_without_approval",
        "target_expansion",
        "unscoped_spider",
    ),
    default_execution_mode="dry_run",
    live_readiness_status="deferred",
    optional_dependency_status="optional_not_required",
    provenance_requirements=(
        "adapter_id",
        "zap_version",
        "policy_profile",
        "sha256",
    ),
)

CAPABILITIES = {
    "supports": list(CONTRACT.supported_capabilities),
    "requires": list(CONTRACT.required_scope_fields + CONTRACT.required_approvals),
    "denies": list(CONTRACT.denied_actions),
}
