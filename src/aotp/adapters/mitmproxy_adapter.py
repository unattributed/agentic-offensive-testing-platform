"""Deferred mitmproxy local capture contract."""

from __future__ import annotations

from ..adapter_contract import AdapterContract

CONTRACT = AdapterContract(
    adapter_id="mitmproxy",
    display_name="mitmproxy authorized local capture contract",
    source_reference="https://docs.mitmproxy.org/stable/addons/overview/",
    supported_capabilities=(
        "authorized_local_capture_placeholder",
        "proxy_capture_placeholder",
    ),
    required_approvals=(
        "explicit_private_scope",
        "policy_gate_approval",
        "future_live_readiness_approval",
        "local_capture_authorization",
    ),
    required_scope_fields=(
        "target_alias",
        "allowed_proxy_context",
        "rate_limits",
        "evidence_rules",
    ),
    required_evidence_handling=(
        "redaction_required",
        "credential_stripping_required",
        "local_only",
        "private_ca_material_excluded",
        "artifact_hash_required",
    ),
    denied_actions=(
        "credential_capture",
        "credential_persistence",
        "live_use_without_approval",
        "private_ca_material_commitment",
        "target_expansion",
        "transparent_interception",
        "unscoped_interception",
    ),
    default_execution_mode="dry_run",
    live_readiness_status="deferred",
    optional_dependency_status="optional_not_required",
    provenance_requirements=(
        "adapter_id",
        "mitmproxy_version",
        "capture_alias",
        "sha256",
    ),
)

CAPABILITIES = {
    "supports": list(CONTRACT.supported_capabilities),
    "requires": list(CONTRACT.required_scope_fields + CONTRACT.required_approvals),
    "denies": list(CONTRACT.denied_actions),
}
