"""Adapter capability registry for AOTP Sprint 4 web contracts."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .control_panel import PANEL_SAFE_OBSERVATIONS, PANEL_UNSAFE_ACTIONS

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

RICH_ADAPTERS: list[dict[str, Any]] = [{'adapter_id': 'playwright',
  'default_execution_mode': 'dry_run',
  'denied_actions': ['live_navigation_by_default',
                     'unscoped_browser_capture',
                     'credential_capture'],
  'display_name': 'Playwright browser evidence contract',
  'live_readiness_status': 'deferred',
  'network_silent_default': True,
  'optional_dependency_status': 'optional_not_required',
  'provenance_requirements': ['adapter_id', 'version', 'local_path_alias', 'sha256'],
  'required_approvals': ['future_live_readiness_approval'],
  'required_evidence_handling': ['redaction_required', 'local_only', 'placeholder_by_default'],
  'required_scope_fields': ['target_alias', 'allowed_urls', 'evidence_rules'],
  'source_reference': 'https://playwright.dev/docs/trace-viewer',
  'supported_capabilities': ['navigation_placeholder',
                             'dom_placeholder',
                             'screenshot_placeholder',
                             'trace_placeholder']},
 {'adapter_id': 'zap',
  'default_execution_mode': 'dry_run',
  'denied_actions': ['active_scan_by_default', 'live_use_without_approval', 'unscoped_spider'],
  'display_name': 'OWASP ZAP web security contract',
  'live_readiness_status': 'deferred',
  'network_silent_default': True,
  'optional_dependency_status': 'optional_not_required',
  'provenance_requirements': ['adapter_id', 'zap_version', 'policy_profile', 'sha256'],
  'required_approvals': ['future_live_readiness_approval', 'explicit_spider_approval'],
  'required_evidence_handling': ['redaction_required', 'local_only'],
  'required_scope_fields': ['target_alias', 'allowed_urls', 'rate_limits', 'evidence_rules'],
  'source_reference': 'https://www.zaproxy.org/docs/automate/automation-framework/',
  'supported_capabilities': ['passive_scan_future_contract', 'limited_spider_future_contract']},
 {'adapter_id': 'mitmproxy',
  'default_execution_mode': 'dry_run',
  'denied_actions': ['unscoped_interception',
                     'private_ca_material_commitment',
                     'credential_capture'],
  'display_name': 'mitmproxy local capture contract',
  'live_readiness_status': 'deferred',
  'network_silent_default': True,
  'optional_dependency_status': 'optional_not_required',
  'provenance_requirements': ['adapter_id', 'mitmproxy_version', 'capture_alias', 'sha256'],
  'required_approvals': ['future_live_readiness_approval', 'local_capture_authorization'],
  'required_evidence_handling': ['redaction_required',
                                 'local_only',
                                 'private_ca_material_excluded'],
  'required_scope_fields': ['target_alias', 'allowed_proxy_context', 'evidence_rules'],
  'source_reference': 'https://docs.mitmproxy.org/stable/',
  'supported_capabilities': ['authorized_local_capture_future_contract',
                             'proxy_capture_placeholder']},
 {'adapter_id': 'osmap',
  'default_execution_mode': 'external_reference_only',
  'denied_actions': ['dependency_import',
                     'vendored_code',
                     'implicit_live_execution',
                     'generated_evidence_commitment'],
  'display_name': 'OSMAP external local evidence contract',
  'live_readiness_status': 'not_applicable_external_reference_only',
  'network_silent_default': True,
  'optional_dependency_status': 'not_a_dependency',
  'provenance_requirements': ['source_project',
                              'commit_or_bundle_alias',
                              'sha256',
                              'redaction_status'],
  'required_approvals': ['external_reference_review'],
  'required_evidence_handling': ['no_vendored_code',
                                 'no_implicit_live_run',
                                 'clean_room_mapping_only'],
  'required_scope_fields': ['evidence_alias', 'relative_path', 'sha256', 'provenance'],
  'source_reference': 'https://github.com/unattributed/OSMAP',
  'supported_capabilities': ['external_local_evidence_reference', 'wstg_mapping_provenance']},
 {'adapter_id': 'browser-suite',
  'default_execution_mode': 'external_reference_only',
  'denied_actions': ['dependency_import',
                     'vendored_code',
                     'implicit_live_execution',
                     'generated_evidence_commitment'],
  'display_name': 'ai-browser-security-test-suite external evidence contract',
  'live_readiness_status': 'not_applicable_external_reference_only',
  'network_silent_default': True,
  'optional_dependency_status': 'not_a_dependency',
  'provenance_requirements': ['source_project', 'artifact_class', 'sha256', 'redaction_status'],
  'required_approvals': ['external_reference_review', 'license_obligation_review'],
  'required_evidence_handling': ['no_vendored_code',
                                 'no_implicit_live_run',
                                 'separate_license_obligations_documented'],
  'required_scope_fields': ['evidence_alias', 'relative_path', 'sha256', 'provenance'],
  'source_reference': 'https://github.com/unattributed/ai-browser-security-test-suite',
  'supported_capabilities': ['external_browser_evidence_reference', 'evidence_class_mapping']}]


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
                "denied_actions": sorted(PANEL_UNSAFE_ACTIONS),
            },
        ]
    }
