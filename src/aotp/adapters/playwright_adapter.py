"""Deferred Playwright browser evidence contract."""

from __future__ import annotations

from ..adapter_contract import AdapterContract

CONTRACT = AdapterContract(
    adapter_id="playwright",
    display_name="Playwright browser evidence contract",
    source_reference="https://playwright.dev/docs/api/class-page",
    supported_capabilities=(
        "navigation_placeholder",
        "dom_placeholder",
        "screenshot_placeholder",
        "trace_placeholder",
    ),
    required_approvals=(
        "explicit_private_scope",
        "policy_gate_approval",
        "future_live_readiness_approval",
    ),
    required_scope_fields=(
        "target_alias",
        "allowed_urls",
        "rate_limits",
        "evidence_rules",
    ),
    required_evidence_handling=(
        "redaction_required",
        "local_only",
        "placeholder_by_default",
        "artifact_hash_required",
    ),
    denied_actions=(
        "credential_capture",
        "credential_guessing",
        "live_navigation_by_default",
        "target_expansion",
        "unscoped_browser_capture",
    ),
    default_execution_mode="dry_run",
    live_readiness_status="deferred",
    optional_dependency_status="optional_not_required",
    provenance_requirements=(
        "adapter_id",
        "version",
        "local_path_alias",
        "sha256",
    ),
)

CAPABILITIES = {
    "supports": list(CONTRACT.supported_capabilities),
    "requires": list(CONTRACT.required_scope_fields + CONTRACT.required_approvals),
    "denies": list(CONTRACT.denied_actions),
}
