"""Adapter capability registry for AOTP Sprint 4 web contracts."""
from __future__ import annotations

from copy import deepcopy
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

ADAPTERS: list[dict[str, Any]] = [
    contract.as_dict()
    for contract in (
        BROWSER_SUITE_CONTRACT,
        MITMPROXY_CONTRACT,
        OSMAP_CONTRACT,
        PLAYWRIGHT_CONTRACT,
        ZAP_CONTRACT,
    )
]

ADAPTER_INDEX = {adapter["adapter_id"]: adapter for adapter in ADAPTERS}
if len(ADAPTER_INDEX) != len(ADAPTERS):
    raise ValueError("adapter contract IDs must be unique")


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
