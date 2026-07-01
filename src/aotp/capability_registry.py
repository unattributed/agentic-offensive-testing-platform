"""Adapter capability registry for AOTP Sprint 4 web contracts."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .control_panel import PANEL_SAFE_OBSERVATIONS, PANEL_UNSAFE_ACTIONS
from .bounded_fuzzing import FUZZING_SAFE_PAYLOAD_CLASSES, FUZZING_UNSAFE_ACTIONS
from .sbom_review import VULNERABILITY_MAPPING_CONTRACT
from .crypto_review import CRYPTO_UNSAFE_ACTIONS
from .adapters.playwright_adapter import CONTRACT as PLAYWRIGHT_CONTRACT
from .adapters.zap_adapter import CONTRACT as ZAP_CONTRACT
from .adapters.mitmproxy_adapter import CONTRACT as MITMPROXY_CONTRACT
from .adapters.osmap_adapter import CONTRACT as OSMAP_CONTRACT
from .adapters.ai_browser_suite_adapter import CONTRACT as BROWSER_SUITE_CONTRACT

@dataclass(frozen=True)
class AdapterCapability:
    adapter: str
    supports: tuple[str, ...]
    requires: tuple[str, ...]
    denies: tuple[str, ...]


REGISTRY: dict[str, AdapterCapability] = {
    "ollama": AdapterCapability(
        "ollama",
        ("structured_planning", "evidence_summarization"),
        ("local_endpoint", "redacted_input"),
        ("scope_authorization", "raw_secrets"),
    ),
    "playwright": AdapterCapability(
        "playwright",
        ("browser_navigation_placeholder", "dom_placeholder", "screenshot_placeholder", "trace_placeholder"),
        ("explicit_target_scope", "rate_limits", "future_live_readiness_approval"),
        ("target_expansion", "credential_guessing", "live_navigation_by_default"),
    ),
    "zap": AdapterCapability(
        "zap",
        ("passive_scan_future_contract", "limited_spider_future_contract"),
        ("explicit_target_scope", "rate_limits", "future_live_readiness_approval"),
        ("active_scan_by_default", "destructive_payloads", "live_use_without_approval"),
    ),
    "mitmproxy": AdapterCapability(
        "mitmproxy",
        ("authorized_proxy_capture_future_contract", "proxy_capture_placeholder"),
        ("explicit_target_scope", "evidence_rules", "local_capture_authorization"),
        ("credential_persistence", "unscoped_interception", "private_ca_material_commitment"),
    ),
    "osmap": AdapterCapability(
        "osmap",
        ("external_local_evidence_reference", "wstg_mapping_provenance"),
        ("local_installation", "external_reference_review"),
        ("implicit_live_execution", "secret_export", "vendored_code", "dependency_import"),
    ),
    "ai_browser_suite": AdapterCapability(
        "ai_browser_suite",
        ("external_browser_evidence_reference", "evidence_class_mapping"),
        ("local_installation", "external_reference_review", "license_obligation_review"),
        ("implicit_live_execution", "unredacted_model_input", "vendored_code", "dependency_import"),
    ),
}

RICH_ADAPTERS: list[dict[str, Any]] = [
 ZAP_CONTRACT.as_dict(),
 PLAYWRIGHT_CONTRACT.as_dict(),
 MITMPROXY_CONTRACT.as_dict(),
 OSMAP_CONTRACT.as_dict(),
 BROWSER_SUITE_CONTRACT.as_dict(),
]


def _legacy_adapter_contract(adapter_id: str, capability: AdapterCapability) -> dict[str, Any]:
    return {
        "adapter_id": adapter_id,
        "display_name": capability.adapter,
        "source_reference": "existing AOTP capability registry",
        "supported_capabilities": list(capability.supports),
        "required_approvals": [],
        "required_scope_fields": list(capability.requires),
        "required_evidence_handling": ["redaction_required", "local_only"],
        "denied_actions": list(capability.denies),
        "default_execution_mode": "dry_run",
        "live_readiness_status": "deferred",
        "optional_dependency_status": "optional_not_required",
        "network_silent_default": True,
        "provenance_requirements": ["adapter_id", "sha256"],
    }


ADAPTERS: list[dict[str, Any]] = RICH_ADAPTERS or [
    _legacy_adapter_contract(adapter_id, capability)
    for adapter_id, capability in REGISTRY.items()
    if adapter_id in {"playwright", "zap", "mitmproxy", "osmap", "ai_browser_suite"}
]

ADAPTER_INDEX = {adapter["adapter_id"]: adapter for adapter in ADAPTERS}


def list_adapters() -> list[dict[str, Any]]:
    return [deepcopy(ADAPTER_INDEX[adapter_id]) for adapter_id in sorted(ADAPTER_INDEX)]


def get_adapter(adapter_id: str) -> dict[str, Any]:
    try:
        return deepcopy(ADAPTER_INDEX[adapter_id])
    except KeyError as exc:
        raise KeyError(f"unknown adapter: {adapter_id}") from exc


def module_summary() -> dict[str, Any]:
    return {
        "modules": [
            {
                "module_id": "wstg_web_application",
                "display_name": "WSTG web application",
                "default_execution_mode": "dry_run",
                "network_silent_default": True,
                "adapter_contracts": [adapter["adapter_id"] for adapter in list_adapters()],
            },
            {
                "module_id": "service_control_panel",
                "display_name": "Service control panel",
                "default_execution_mode": "dry_run",
                "network_silent_default": True,
                "adapter_contracts": [],
                "required_scope_fields": ["target_alias", "panel_alias"],
                "supported_capabilities": sorted(PANEL_SAFE_OBSERVATIONS),
                "evidence_artifacts": ["evidence.json", "panel-evidence.json"],
                "report_inclusion_status": "excluded_pending_review",
                "report_review_gating": True,
                "denied_actions": sorted(PANEL_UNSAFE_ACTIONS),
            },
            {
                "module_id": "bounded_fuzzing",
                "display_name": "Bounded fuzzing",
                "default_execution_mode": "dry_run",
                "network_silent_default": True,
                "adapter_contracts": [],
                "required_scope_fields": [
                    "target_alias",
                    "api",
                    "payload_budget",
                    "request_budget",
                    "per_endpoint_limit",
                ],
                "supported_capabilities": sorted(FUZZING_SAFE_PAYLOAD_CLASSES),
                "evidence_artifacts": ["evidence.json", "fuzzing-evidence.json"],
                "denied_actions": sorted(FUZZING_UNSAFE_ACTIONS),
            },
            {
                "module_id": "sbom_review",
                "display_name": "SBOM and dependency review",
                "default_execution_mode": "dry_run",
                "network_silent_default": True,
                "adapter_contracts": [],
                "required_scope_fields": ["target_alias", "artifact"],
                "supported_capabilities": [
                    "component_inventory",
                    "manifest",
                    "lockfile",
                    "sbom",
                ],
                "evidence_artifacts": ["evidence.json", "sbom-evidence.json"],
                "vulnerability_mapping_contract": VULNERABILITY_MAPPING_CONTRACT,
                "denied_actions": [
                    "implicit_external_lookup",
                    "unprovided_artifacts",
                    "unverified_exploitability_claims",
                ],
            },
            {
                "module_id": "crypto_controls",
                "display_name": "Cryptographic controls review",
                "default_execution_mode": "dry_run",
                "network_silent_default": True,
                "adapter_contracts": [],
                "required_scope_fields": ["target_alias", "cryptographic_controls"],
                "supported_capabilities": [
                    "certificate_metadata",
                    "cookie_attributes",
                    "key_management_metadata",
                    "tls",
                    "token_configuration",
                    "weak_algorithm_indicators",
                ],
                "evidence_artifacts": ["evidence.json", "crypto-evidence.json"],
                "denied_actions": sorted(CRYPTO_UNSAFE_ACTIONS),
            },
        ]
    }
