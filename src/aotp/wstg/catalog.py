"""Canonical OWASP WSTG v4.2 catalog used by the AOTP WSTG engine.

This module is intentionally data-heavy. It exists so AOTP can plan against the
complete stable OWASP Web Security Testing Guide v4.2 test set without inventing
or reassigning official WSTG identifiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


class WSTGCatalogError(ValueError):
    """Raised when the canonical WSTG catalog is malformed or incomplete."""


class WSTGAutomationStatus(str, Enum):
    """AOTP implementation status for a WSTG test case."""

    AUTOMATED = "automated"
    SEMI_AUTOMATED = "semi_automated"
    MANUAL = "manual"
    NOT_SUPPORTED = "not_supported"


class WSTGSafetyTier(str, Enum):
    """Execution safety tier for WSTG planning and approval gates."""

    PASSIVE = "passive"
    SAFE_ACTIVE = "safe_active"
    INTRUSIVE_ACTIVE = "intrusive_active"
    DESTRUCTIVE_DENIED = "destructive_denied"


class WSTGAuthRequirement(str, Enum):
    """Authentication context needed before a test can be executed."""

    ANONYMOUS = "anonymous"
    AUTHENTICATED = "authenticated"
    MULTI_ROLE = "multi_role"
    PRIVILEGED = "privileged"
    SOURCE_ASSISTED = "source_assisted"


class WSTGAdapterFamily(str, Enum):
    """Generic AOTP adapter family, never an application-specific dependency."""

    HTTP = "http"
    BROWSER = "browser"
    PROXY = "proxy"
    TLS = "tls"
    API = "api"
    SOURCE_REVIEW = "source_review"
    MANUAL = "manual"
    MULTI_STEP = "multi_step"


_WSTG_VERSION_RE = re.compile(r"^v[0-9]+$")
_WSTG_ID_RE = re.compile(r"^WSTG-v[0-9]+-[A-Z]{4}-[0-9]{2}$")

_CATEGORY_NAMES: dict[str, str] = {'INFO': 'Information Gathering', 'CONF': 'Configuration and Deployment Management Testing', 'IDNT': 'Identity Management Testing', 'ATHN': 'Authentication Testing', 'ATHZ': 'Authorization Testing', 'SESS': 'Session Management Testing', 'INPV': 'Input Validation Testing', 'ERRH': 'Testing for Error Handling', 'CRYP': 'Testing for Weak Cryptography', 'BUSL': 'Business Logic Testing', 'CLNT': 'Client-side Testing', 'APIT': 'API Testing'}
_CATEGORY_PATHS: dict[str, str] = {'INFO': '01-Information_Gathering', 'CONF': '02-Configuration_and_Deployment_Management_Testing', 'IDNT': '03-Identity_Management_Testing', 'ATHN': '04-Authentication_Testing', 'ATHZ': '05-Authorization_Testing', 'SESS': '06-Session_Management_Testing', 'INPV': '07-Input_Validation_Testing', 'ERRH': '08-Testing_for_Error_Handling', 'CRYP': '09-Testing_for_Weak_Cryptography', 'BUSL': '10-Business_Logic_Testing', 'CLNT': '11-Client-side_Testing', 'APIT': '12-API_Testing'}
_EXPECTED_CATEGORY_COUNTS: dict[str, int] = {
    "INFO": 10,
    "CONF": 11,
    "IDNT": 5,
    "ATHN": 10,
    "ATHZ": 4,
    "SESS": 9,
    "INPV": 19,
    "ERRH": 2,
    "CRYP": 4,
    "BUSL": 9,
    "CLNT": 13,
    "APIT": 1,
}
EXPECTED_WSTG_V42_TEST_COUNT = sum(_EXPECTED_CATEGORY_COUNTS.values())


@dataclass(frozen=True)
class WSTGTestCase:
    """One canonical OWASP WSTG test case plus AOTP execution metadata."""

    wstg_id: str
    version: str
    category: str
    category_name: str
    sequence: int
    title: str
    source_url: str
    automation_status: WSTGAutomationStatus
    safety_tier: WSTGSafetyTier
    auth_requirement: WSTGAuthRequirement
    adapter_family: WSTGAdapterFamily
    evidence_required: tuple[str, ...]

    def __post_init__(self) -> None:
        if _WSTG_ID_RE.fullmatch(self.wstg_id) is None:
            raise WSTGCatalogError("wstg_id must be version-qualified, for example WSTG-v42-INFO-02")
        if not _WSTG_VERSION_RE.fullmatch(self.version):
            raise WSTGCatalogError("version must be a compact WSTG version such as v42")
        if self.version not in self.wstg_id:
            raise WSTGCatalogError("test case version must appear in the WSTG identifier")
        if self.category not in _CATEGORY_NAMES:
            raise WSTGCatalogError(f"unknown WSTG category: {self.category}")
        if self.category_name != _CATEGORY_NAMES[self.category]:
            raise WSTGCatalogError("category_name must match the canonical category map")
        if self.sequence < 1:
            raise WSTGCatalogError("sequence must be positive")
        if not self.title.strip():
            raise WSTGCatalogError("WSTG title is required")
        if "/www-project-web-security-testing-guide/v42/" not in self.source_url:
            raise WSTGCatalogError("source_url must reference the OWASP WSTG v4.2 guide")
        if not self.evidence_required:
            raise WSTGCatalogError("evidence_required must not be empty")

    @property
    def short_id(self) -> str:
        return self.wstg_id.replace(f"WSTG-{self.version}-", "WSTG-")

    @property
    def sort_key(self) -> tuple[int, int]:
        categories = list(_EXPECTED_CATEGORY_COUNTS)
        return (categories.index(self.category), self.sequence)

    def as_dict(self) -> dict[str, Any]:
        return {
            "wstg_id": self.wstg_id,
            "short_id": self.short_id,
            "version": self.version,
            "category": self.category,
            "category_name": self.category_name,
            "sequence": self.sequence,
            "title": self.title,
            "source_url": self.source_url,
            "automation_status": self.automation_status.value,
            "safety_tier": self.safety_tier.value,
            "auth_requirement": self.auth_requirement.value,
            "adapter_family": self.adapter_family.value,
            "evidence_required": list(self.evidence_required),
        }


class WSTGCatalog:
    """Immutable WSTG catalog with completeness checks."""

    def __init__(self, cases: Iterable[WSTGTestCase]) -> None:
        ordered = tuple(sorted(cases, key=lambda item: item.sort_key))
        if not ordered:
            raise WSTGCatalogError("at least one WSTG test case is required")
        seen: set[str] = set()
        counts = {category: 0 for category in _EXPECTED_CATEGORY_COUNTS}
        for case in ordered:
            if case.wstg_id in seen:
                raise WSTGCatalogError(f"duplicate WSTG identifier: {case.wstg_id}")
            seen.add(case.wstg_id)
            counts[case.category] += 1
        if counts != _EXPECTED_CATEGORY_COUNTS:
            raise WSTGCatalogError(f"incomplete WSTG v4.2 catalog: {counts!r}")
        self._cases = ordered
        self._by_id = {case.wstg_id: case for case in ordered}

    def cases(self) -> tuple[WSTGTestCase, ...]:
        return self._cases

    def by_id(self, wstg_id: str) -> WSTGTestCase:
        try:
            return self._by_id[wstg_id]
        except KeyError as exc:
            raise WSTGCatalogError(f"unknown WSTG identifier: {wstg_id}") from exc

    def by_category(self, category: str) -> tuple[WSTGTestCase, ...]:
        if category not in _EXPECTED_CATEGORY_COUNTS:
            raise WSTGCatalogError(f"unknown WSTG category: {category}")
        return tuple(case for case in self._cases if case.category == category)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": "v42",
            "test_count": len(self._cases),
            "category_counts": {category: len(self.by_category(category)) for category in _EXPECTED_CATEGORY_COUNTS},
            "cases": [case.as_dict() for case in self._cases],
        }


_RAW_V42_CASES = (
    ('INFO', 1, 'Conduct Search Engine Discovery Reconnaissance for Information Leakage', 'automated', 'passive', 'anonymous', 'http', ('target_surface', 'request_response_metadata', 'operator_notes')),
    ('INFO', 2, 'Fingerprint Web Server', 'automated', 'passive', 'anonymous', 'http', ('target_surface', 'request_response_metadata', 'operator_notes')),
    ('INFO', 3, 'Review Webserver Metafiles for Information Leakage', 'automated', 'passive', 'anonymous', 'http', ('target_surface', 'request_response_metadata', 'operator_notes')),
    ('INFO', 4, 'Enumerate Applications on Webserver', 'automated', 'passive', 'anonymous', 'http', ('target_surface', 'request_response_metadata', 'operator_notes')),
    ('INFO', 5, 'Review Webpage Content for Information Leakage', 'automated', 'passive', 'anonymous', 'http', ('target_surface', 'request_response_metadata', 'operator_notes')),
    ('INFO', 6, 'Identify Application Entry Points', 'automated', 'passive', 'anonymous', 'http', ('target_surface', 'request_response_metadata', 'operator_notes')),
    ('INFO', 7, 'Map Execution Paths Through Application', 'automated', 'passive', 'anonymous', 'http', ('target_surface', 'request_response_metadata', 'operator_notes')),
    ('INFO', 8, 'Fingerprint Web Application Framework', 'automated', 'passive', 'anonymous', 'http', ('target_surface', 'request_response_metadata', 'operator_notes')),
    ('INFO', 9, 'Fingerprint Web Application', 'automated', 'passive', 'anonymous', 'http', ('target_surface', 'request_response_metadata', 'operator_notes')),
    ('INFO', 10, 'Map Application Architecture', 'automated', 'passive', 'anonymous', 'http', ('target_surface', 'request_response_metadata', 'operator_notes')),
    ('CONF', 1, 'Test Network Infrastructure Configuration', 'semi_automated', 'safe_active', 'anonymous', 'http', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('CONF', 2, 'Test Application Platform Configuration', 'automated', 'passive', 'anonymous', 'http', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('CONF', 3, 'Test File Extensions Handling for Sensitive Information', 'automated', 'passive', 'anonymous', 'http', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('CONF', 4, 'Review Old Backup and Unreferenced Files for Sensitive Information', 'automated', 'passive', 'anonymous', 'http', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('CONF', 5, 'Enumerate Infrastructure and Application Admin Interfaces', 'automated', 'passive', 'anonymous', 'http', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('CONF', 6, 'Test HTTP Methods', 'automated', 'safe_active', 'anonymous', 'http', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('CONF', 7, 'Test HTTP Strict Transport Security', 'automated', 'passive', 'anonymous', 'tls', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('CONF', 8, 'Test RIA Cross Domain Policy', 'automated', 'passive', 'anonymous', 'http', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('CONF', 9, 'Test File Permission', 'semi_automated', 'safe_active', 'anonymous', 'http', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('CONF', 10, 'Test for Subdomain Takeover', 'semi_automated', 'safe_active', 'anonymous', 'http', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('CONF', 11, 'Test Cloud Storage', 'semi_automated', 'safe_active', 'anonymous', 'http', ('configuration_observation', 'request_response_metadata', 'scope_boundary')),
    ('IDNT', 1, 'Test Role Definitions', 'manual', 'safe_active', 'multi_role', 'manual', ('identity_workflow_notes', 'role_matrix', 'redacted_account_aliases')),
    ('IDNT', 2, 'Test User Registration Process', 'manual', 'safe_active', 'authenticated', 'manual', ('identity_workflow_notes', 'role_matrix', 'redacted_account_aliases')),
    ('IDNT', 3, 'Test Account Provisioning Process', 'manual', 'safe_active', 'multi_role', 'manual', ('identity_workflow_notes', 'role_matrix', 'redacted_account_aliases')),
    ('IDNT', 4, 'Testing for Account Enumeration and Guessable User Account', 'manual', 'safe_active', 'multi_role', 'manual', ('identity_workflow_notes', 'role_matrix', 'redacted_account_aliases')),
    ('IDNT', 5, 'Testing for Weak or Unenforced Username Policy', 'manual', 'safe_active', 'authenticated', 'manual', ('identity_workflow_notes', 'role_matrix', 'redacted_account_aliases')),
    ('ATHN', 1, 'Testing for Credentials Transported over an Encrypted Channel', 'semi_automated', 'safe_active', 'anonymous', 'multi_step', ('auth_flow_observation', 'redacted_request_response', 'lockout_stop_condition')),
    ('ATHN', 2, 'Testing for Default Credentials', 'semi_automated', 'safe_active', 'anonymous', 'multi_step', ('auth_flow_observation', 'redacted_request_response', 'lockout_stop_condition')),
    ('ATHN', 3, 'Testing for Weak Lock Out Mechanism', 'semi_automated', 'safe_active', 'anonymous', 'multi_step', ('auth_flow_observation', 'redacted_request_response', 'lockout_stop_condition')),
    ('ATHN', 4, 'Testing for Bypassing Authentication Schema', 'semi_automated', 'safe_active', 'anonymous', 'multi_step', ('auth_flow_observation', 'redacted_request_response', 'lockout_stop_condition')),
    ('ATHN', 5, 'Testing for Vulnerable Remember Password', 'semi_automated', 'safe_active', 'authenticated', 'multi_step', ('auth_flow_observation', 'redacted_request_response', 'lockout_stop_condition')),
    ('ATHN', 6, 'Testing for Browser Cache Weaknesses', 'semi_automated', 'safe_active', 'authenticated', 'multi_step', ('auth_flow_observation', 'redacted_request_response', 'lockout_stop_condition')),
    ('ATHN', 7, 'Testing for Weak Password Policy', 'semi_automated', 'safe_active', 'anonymous', 'multi_step', ('auth_flow_observation', 'redacted_request_response', 'lockout_stop_condition')),
    ('ATHN', 8, 'Testing for Weak Security Question Answer', 'semi_automated', 'safe_active', 'authenticated', 'multi_step', ('auth_flow_observation', 'redacted_request_response', 'lockout_stop_condition')),
    ('ATHN', 9, 'Testing for Weak Password Change or Reset Functionalities', 'semi_automated', 'safe_active', 'authenticated', 'multi_step', ('auth_flow_observation', 'redacted_request_response', 'lockout_stop_condition')),
    ('ATHN', 10, 'Testing for Weaker Authentication in Alternative Channel', 'semi_automated', 'safe_active', 'anonymous', 'multi_step', ('auth_flow_observation', 'redacted_request_response', 'lockout_stop_condition')),
    ('ATHZ', 1, 'Testing Directory Traversal File Include', 'semi_automated', 'safe_active', 'multi_role', 'multi_step', ('authorization_matrix', 'redacted_account_aliases', 'redacted_request_response')),
    ('ATHZ', 2, 'Testing for Bypassing Authorization Schema', 'semi_automated', 'safe_active', 'multi_role', 'multi_step', ('authorization_matrix', 'redacted_account_aliases', 'redacted_request_response')),
    ('ATHZ', 3, 'Testing for Privilege Escalation', 'semi_automated', 'safe_active', 'multi_role', 'multi_step', ('authorization_matrix', 'redacted_account_aliases', 'redacted_request_response')),
    ('ATHZ', 4, 'Testing for Insecure Direct Object References', 'semi_automated', 'safe_active', 'multi_role', 'multi_step', ('authorization_matrix', 'redacted_account_aliases', 'redacted_request_response')),
    ('SESS', 1, 'Testing for Session Management Schema', 'semi_automated', 'safe_active', 'authenticated', 'browser', ('session_observation', 'redacted_cookie_metadata', 'vault_handle_if_sensitive')),
    ('SESS', 2, 'Testing for Cookies Attributes', 'semi_automated', 'safe_active', 'authenticated', 'browser', ('session_observation', 'redacted_cookie_metadata', 'vault_handle_if_sensitive')),
    ('SESS', 3, 'Testing for Session Fixation', 'semi_automated', 'safe_active', 'authenticated', 'browser', ('session_observation', 'redacted_cookie_metadata', 'vault_handle_if_sensitive')),
    ('SESS', 4, 'Testing for Exposed Session Variables', 'semi_automated', 'safe_active', 'authenticated', 'browser', ('session_observation', 'redacted_cookie_metadata', 'vault_handle_if_sensitive')),
    ('SESS', 5, 'Testing for Cross Site Request Forgery', 'semi_automated', 'safe_active', 'multi_role', 'browser', ('session_observation', 'redacted_cookie_metadata', 'vault_handle_if_sensitive')),
    ('SESS', 6, 'Testing for Logout Functionality', 'semi_automated', 'safe_active', 'authenticated', 'browser', ('session_observation', 'redacted_cookie_metadata', 'vault_handle_if_sensitive')),
    ('SESS', 7, 'Testing Session Timeout', 'semi_automated', 'safe_active', 'authenticated', 'browser', ('session_observation', 'redacted_cookie_metadata', 'vault_handle_if_sensitive')),
    ('SESS', 8, 'Testing for Session Puzzling', 'semi_automated', 'safe_active', 'authenticated', 'browser', ('session_observation', 'redacted_cookie_metadata', 'vault_handle_if_sensitive')),
    ('SESS', 9, 'Testing for Session Hijacking', 'semi_automated', 'safe_active', 'authenticated', 'browser', ('session_observation', 'redacted_cookie_metadata', 'vault_handle_if_sensitive')),
    ('INPV', 1, 'Testing for Reflected Cross Site Scripting', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 2, 'Testing for Stored Cross Site Scripting', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 3, 'Testing for HTTP Verb Tampering', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 4, 'Testing for HTTP Parameter Pollution', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 5, 'Testing for SQL Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 6, 'Testing for LDAP Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 7, 'Testing for XML Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 8, 'Testing for SSI Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 9, 'Testing for XPath Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 10, 'Testing for IMAP SMTP Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 11, 'Testing for Code Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 12, 'Testing for Command Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 13, 'Testing for Format String Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 14, 'Testing for Incubated Vulnerability', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 15, 'Testing for HTTP Splitting Smuggling', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 16, 'Testing for HTTP Incoming Requests', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 17, 'Testing for Host Header Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 18, 'Testing for Server-side Template Injection', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('INPV', 19, 'Testing for Server-Side Request Forgery', 'semi_automated', 'intrusive_active', 'anonymous', 'http', ('entry_point', 'safe_payload_class', 'request_budget', 'redacted_request_response')),
    ('ERRH', 1, 'Testing for Improper Error Handling', 'semi_automated', 'safe_active', 'anonymous', 'http', ('bounded_error_observation', 'redacted_response_excerpt', 'stop_condition')),
    ('ERRH', 2, 'Testing for Stack Traces', 'semi_automated', 'safe_active', 'anonymous', 'http', ('bounded_error_observation', 'redacted_response_excerpt', 'stop_condition')),
    ('CRYP', 1, 'Testing for Weak Transport Layer Security', 'automated', 'passive', 'anonymous', 'tls', ('crypto_observation', 'configuration_evidence', 'manual_review_notes')),
    ('CRYP', 2, 'Testing for Padding Oracle', 'manual', 'safe_active', 'anonymous', 'manual', ('crypto_observation', 'configuration_evidence', 'manual_review_notes')),
    ('CRYP', 3, 'Testing for Sensitive Information Sent via Unencrypted Channels', 'manual', 'safe_active', 'anonymous', 'manual', ('crypto_observation', 'configuration_evidence', 'manual_review_notes')),
    ('CRYP', 4, 'Testing for Weak Encryption', 'manual', 'safe_active', 'anonymous', 'manual', ('crypto_observation', 'configuration_evidence', 'manual_review_notes')),
    ('BUSL', 1, 'Test Business Logic Data Validation', 'manual', 'intrusive_active', 'multi_role', 'manual', ('business_rule', 'workflow_trace', 'operator_hypothesis', 'redacted_evidence')),
    ('BUSL', 2, 'Test Ability to Forge Requests', 'manual', 'intrusive_active', 'multi_role', 'manual', ('business_rule', 'workflow_trace', 'operator_hypothesis', 'redacted_evidence')),
    ('BUSL', 3, 'Test Integrity Checks', 'manual', 'intrusive_active', 'multi_role', 'manual', ('business_rule', 'workflow_trace', 'operator_hypothesis', 'redacted_evidence')),
    ('BUSL', 4, 'Test for Process Timing', 'manual', 'intrusive_active', 'multi_role', 'manual', ('business_rule', 'workflow_trace', 'operator_hypothesis', 'redacted_evidence')),
    ('BUSL', 5, 'Test Number of Times a Function Can Be Used Limits', 'manual', 'intrusive_active', 'multi_role', 'manual', ('business_rule', 'workflow_trace', 'operator_hypothesis', 'redacted_evidence')),
    ('BUSL', 6, 'Testing for the Circumvention of Work Flows', 'manual', 'intrusive_active', 'multi_role', 'manual', ('business_rule', 'workflow_trace', 'operator_hypothesis', 'redacted_evidence')),
    ('BUSL', 7, 'Test Defenses Against Application Misuse', 'manual', 'intrusive_active', 'multi_role', 'manual', ('business_rule', 'workflow_trace', 'operator_hypothesis', 'redacted_evidence')),
    ('BUSL', 8, 'Test Upload of Unexpected File Types', 'manual', 'intrusive_active', 'multi_role', 'manual', ('business_rule', 'workflow_trace', 'operator_hypothesis', 'redacted_evidence')),
    ('BUSL', 9, 'Test Upload of Malicious Files', 'manual', 'intrusive_active', 'multi_role', 'manual', ('business_rule', 'workflow_trace', 'operator_hypothesis', 'redacted_evidence')),
    ('CLNT', 1, 'Testing for DOM-Based Cross Site Scripting', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 2, 'Testing for JavaScript Execution', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 3, 'Testing for HTML Injection', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 4, 'Testing for Client-side URL Redirect', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 5, 'Testing for CSS Injection', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 6, 'Testing for Client-side Resource Manipulation', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 7, 'Testing Cross Origin Resource Sharing', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 8, 'Testing for Cross Site Flashing', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 9, 'Testing for Clickjacking', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 10, 'Testing WebSockets', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 11, 'Testing Web Messaging', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 12, 'Testing Browser Storage', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('CLNT', 13, 'Testing for Cross Site Script Inclusion', 'semi_automated', 'safe_active', 'anonymous', 'browser', ('browser_observation', 'dom_snapshot_or_metadata', 'redacted_console_or_network')),
    ('APIT', 1, 'Testing GraphQL', 'semi_automated', 'safe_active', 'anonymous', 'api', ('api_schema_or_endpoint', 'request_response_metadata', 'rate_limit_boundary')),
)


def _source_url(version: str, category: str, sequence: int, title: str) -> str:
    category_path = _CATEGORY_PATHS[category]
    page_slug = title.replace("/", "_").replace(" ", "_")
    return (
        "https://owasp.org/www-project-web-security-testing-guide/"
        f"{version}/4-Web_Application_Security_Testing/{category_path}/{sequence:02d}-{page_slug}"
    )


def build_wstg_v42_catalog() -> WSTGCatalog:
    """Build the complete canonical OWASP WSTG v4.2 catalog."""

    version = "v42"
    cases = []
    for category, sequence, title, automation_status, safety_tier, auth_requirement, adapter_family, evidence_required in _RAW_V42_CASES:
        cases.append(
            WSTGTestCase(
                wstg_id=f"WSTG-{version}-{category}-{sequence:02d}",
                version=version,
                category=category,
                category_name=_CATEGORY_NAMES[category],
                sequence=sequence,
                title=title,
                source_url=_source_url(version, category, sequence, title),
                automation_status=WSTGAutomationStatus(automation_status),
                safety_tier=WSTGSafetyTier(safety_tier),
                auth_requirement=WSTGAuthRequirement(auth_requirement),
                adapter_family=WSTGAdapterFamily(adapter_family),
                evidence_required=tuple(evidence_required),
            )
        )
    return WSTGCatalog(cases)


WSTG_V42_CATALOG = build_wstg_v42_catalog()
