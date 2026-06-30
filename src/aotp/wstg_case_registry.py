"""AOTP-native WSTG case registry for dry-run safe Sprint 4 cases."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

CASES: list[dict[str, Any]] = [{'adapter_capability_requirements': ['network_silent', 'dry_run'],
  'approval_scope': 'none',
  'approved_actions': ['list_case_metadata', 'dry_run_evidence_placeholder'],
  'artifact_placeholders': [],
  'case_id': 'wstg-registry-smoke',
  'denied_actions': ['network_request', 'crawl', 'scan', 'mutation', 'credential_guessing'],
  'evidence_mappings': ['case_id',
                        'wstg_mapping',
                        'module',
                        'target_alias',
                        'policy_decision',
                        'execution_mode'],
  'human_approval_required': False,
  'module': 'wstg_web_application',
  'title': 'WSTG registry dry-run smoke case',
  'wstg': [{'id': 'WSTG-INFO-01',
            'name': 'Conduct Search Engine Discovery Reconnaissance for Information Leakage',
            'version': '4.2'}]},
 {'adapter_capability_requirements': ['network_silent', 'dry_run', 'redaction_required'],
  'approval_scope': 'provisioned_account_observation_only',
  'approved_actions': ['observe_provisioned_account_login_metadata',
                       'record_redacted_placeholder_evidence'],
  'artifact_placeholders': ['redacted_authn_observation'],
  'case_id': 'wstg-authn-provisioned-account-observation',
  'denied_actions': ['credential_guessing',
                     'brute_force',
                     'password_spraying',
                     'credential_stuffing',
                     'account_enumeration',
                     'lockout_triggering'],
  'evidence_mappings': ['case_id',
                        'wstg_mapping',
                        'target_alias',
                        'redacted_account_alias',
                        'policy_decision',
                        'request_count'],
  'human_approval_required': False,
  'module': 'wstg_web_application',
  'title': 'Provisioned-account authentication observation',
  'wstg': [{'id': 'WSTG-ATHN-01',
            'name': 'Testing for Credentials Transported over an Encrypted Channel',
            'version': '4.2'}]},
 {'adapter_capability_requirements': ['network_silent', 'dry_run', 'redaction_required'],
  'approval_scope': 'provisioned_session_observation_only',
  'approved_actions': ['observe_session_attribute_metadata',
                       'record_redacted_placeholder_evidence'],
  'artifact_placeholders': ['redacted_session_attribute_observation'],
  'case_id': 'wstg-session-attribute-observation',
  'denied_actions': ['token_theft',
                     'token_replay',
                     'session_hijacking',
                     'session_replay',
                     'credential_stuffing'],
  'evidence_mappings': ['case_id',
                        'wstg_mapping',
                        'target_alias',
                        'cookie_attribute_aliases',
                        'policy_decision',
                        'request_count'],
  'human_approval_required': False,
  'module': 'wstg_web_application',
  'title': 'Session attribute observation',
  'wstg': [{'id': 'WSTG-SESS-02', 'name': 'Testing for Cookies Attributes', 'version': '4.2'}]},
 {'adapter_capability_requirements': ['network_silent', 'dry_run', 'human_approval_gate'],
  'approval_scope': 'objective_specific_cross_account_confirmation',
  'approved_actions': ['model_cross_account_confirmation_objective', 'pause_for_human_approval'],
  'artifact_placeholders': ['authorization_gate_record'],
  'case_id': 'wstg-authz-cross-account-confirmation',
  'denied_actions': ['exploit',
                     'mutate',
                     'enumerate',
                     'bypass',
                     'access_other_account',
                     'session_replay'],
  'evidence_mappings': ['case_id',
                        'wstg_mapping',
                        'target_alias',
                        'policy_decision',
                        'human_approval_status'],
  'human_approval_required': True,
  'module': 'wstg_web_application',
  'title': 'Cross-account authorization confirmation gate',
  'wstg': [{'id': 'WSTG-ATHZ-01',
            'name': 'Testing Directory Traversal File Include',
            'version': '4.2'},
           {'id': 'WSTG-ATHZ-04',
            'name': 'Testing for Insecure Direct Object References',
            'version': '4.2'}]},
 {'adapter_capability_requirements': ['network_silent', 'dry_run', 'reporter_evidence_binding'],
  'approval_scope': 'observation_only_headers',
  'approved_actions': ['dry_run_header_evidence_model', 'record_header_placeholder_artifacts'],
  'artifact_placeholders': ['header_summary_placeholder',
                            'raw_header_placeholder',
                            'redacted_header_placeholder'],
  'case_id': 'wstg-security-header-review',
  'denied_actions': ['traffic',
                     'mutation',
                     'crawl',
                     'spider',
                     'authentication',
                     'infer_finding_without_evidence'],
  'evidence_mappings': ['case_id',
                        'wstg_mapping',
                        'module',
                        'target_alias',
                        'policy_decision',
                        'execution_mode',
                        'request_count',
                        'verifier_verdict',
                        'confidence',
                        'artifact_placeholders',
                        'redaction_status'],
  'human_approval_required': False,
  'module': 'wstg_web_application',
  'title': 'Observation-only security header review',
  'wstg': [{'id': 'WSTG-CONF-12', 'name': 'Testing for Content Security Policy', 'version': '4.2'},
           {'id': 'WSTG-CONF-07',
            'name': 'Test HTTP Strict Transport Security',
            'version': '4.2'}]},
 {'adapter_capability_requirements': ['network_silent',
                                      'dry_run',
                                      'external_reference_validation',
                                      'redaction_required'],
  'approval_scope': 'placeholder_only_browser_context',
  'approved_actions': ['model_browser_context_placeholders', 'reference_external_local_evidence'],
  'artifact_placeholders': ['dom_snapshot',
                            'rendered_page_summary',
                            'screenshot_placeholder',
                            'frame_tree_placeholder',
                            'browser_context_placeholder',
                            'storage_state_placeholder',
                            'proxy_capture_placeholder'],
  'case_id': 'wstg-browser-context-evidence',
  'denied_actions': ['live_playwright_execution',
                     'live_proxy_execution',
                     'capture_real_browser_data',
                     'unredacted_storage_capture',
                     'path_escape'],
  'evidence_mappings': ['dom_snapshot',
                        'rendered_page_summary',
                        'screenshot_placeholder',
                        'frame_tree_placeholder',
                        'browser_context_placeholder',
                        'storage_state_placeholder',
                        'proxy_capture_placeholder'],
  'human_approval_required': False,
  'module': 'wstg_web_application',
  'title': 'Browser-agent context evidence placeholder model',
  'wstg': [{'id': 'WSTG-CLNT-01',
            'name': 'Testing for DOM-Based Cross Site Scripting',
            'version': '4.2'},
           {'id': 'WSTG-CLNT-12', 'name': 'Testing Browser Storage', 'version': '4.2'}]}]

CASE_INDEX = {case["case_id"]: case for case in CASES}


def list_cases() -> list[dict[str, Any]]:
    return [deepcopy(CASE_INDEX[case_id]) for case_id in sorted(CASE_INDEX)]


def get_case(case_id: str) -> dict[str, Any]:
    try:
        return deepcopy(CASE_INDEX[case_id])
    except KeyError as exc:
        raise KeyError(f"unknown WSTG case: {case_id}") from exc


def case_ids() -> list[str]:
    return sorted(CASE_INDEX)


def case_summary_rows() -> list[dict[str, Any]]:
    rows = []
    for case in list_cases():
        rows.append({
            "case_id": case["case_id"],
            "module": case["module"],
            "human_approval_required": case["human_approval_required"],
            "wstg_ids": [entry["id"] for entry in case["wstg"]],
            "adapter_capability_requirements": case["adapter_capability_requirements"],
        })
    return rows


def build_dry_run_record(case_id: str, target_alias: str = "example-target", approved: bool = False) -> dict[str, Any]:
    case = get_case(case_id)
    if case["human_approval_required"] and not approved:
        decision = "paused_human_approval_required"
        verdict = "stopped_by_policy"
    else:
        decision = "allowed_dry_run"
        verdict = "manual_review"
    return {
        "case_id": case["case_id"],
        "title": case["title"],
        "wstg_mapping": case["wstg"],
        "module": case["module"],
        "target_alias": target_alias,
        "policy_decision": decision,
        "execution_mode": "dry_run",
        "request_count": 0,
        "verifier_verdict": verdict,
        "confidence": "not_assessed",
        "artifact_placeholders": case["artifact_placeholders"],
        "redaction_status": "placeholder_only_no_private_material",
        "approved_actions": case["approved_actions"],
        "denied_actions": case["denied_actions"],
        "human_approval_required": case["human_approval_required"],
        "adapter_capability_requirements": case["adapter_capability_requirements"],
    }
