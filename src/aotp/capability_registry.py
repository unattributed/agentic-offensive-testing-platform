"""Adapter capability declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdapterCapability:
    adapter: str
    supports: tuple[str, ...]
    requires: tuple[str, ...]
    denies: tuple[str, ...]


REGISTRY = {
    "ollama": AdapterCapability(
        "ollama",
        ("structured_planning", "evidence_summarization"),
        ("local_endpoint", "redacted_input"),
        ("scope_authorization", "raw_secrets"),
    ),
    "playwright": AdapterCapability(
        "playwright",
        ("browser_navigation", "dom_capture", "trace_capture"),
        ("explicit_target_scope", "rate_limits"),
        ("target_expansion", "credential_guessing"),
    ),
    "zap": AdapterCapability(
        "zap",
        ("passive_scan", "spider_limited"),
        ("explicit_target_scope", "rate_limits"),
        ("active_scan_without_approval", "destructive_payloads"),
    ),
    "mitmproxy": AdapterCapability(
        "mitmproxy",
        ("authorized_proxy_capture",),
        ("explicit_target_scope", "evidence_rules"),
        ("credential_persistence", "unscoped_interception"),
    ),
    "osmap": AdapterCapability(
        "osmap",
        ("authorized_mailbox_case_bridge",),
        ("local_installation", "explicit_target_scope"),
        ("implicit_live_execution", "secret_export"),
    ),
    "ai_browser_suite": AdapterCapability(
        "ai_browser_suite",
        ("browser_ai_evidence_bridge",),
        ("local_installation", "explicit_target_scope"),
        ("implicit_live_execution", "unredacted_model_input"),
    ),
}
