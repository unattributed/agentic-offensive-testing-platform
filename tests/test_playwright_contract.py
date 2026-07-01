from __future__ import annotations

from dataclasses import replace

import pytest

from aotp.adapters.playwright_adapter import CAPABILITIES, CONTRACT
from aotp.capability_registry import get_adapter


def test_playwright_contract_declares_browser_artifacts_scope_and_rates():
    assert CONTRACT.supported_capabilities == (
        "navigation_placeholder",
        "dom_placeholder",
        "screenshot_placeholder",
        "trace_placeholder",
    )
    assert {"target_alias", "allowed_urls", "rate_limits", "evidence_rules"}.issubset(
        CONTRACT.required_scope_fields
    )
    assert "artifact_hash_required" in CONTRACT.required_evidence_handling
    assert "explicit_private_scope" in CONTRACT.required_approvals
    assert "policy_gate_approval" in CONTRACT.required_approvals


def test_playwright_contract_is_network_silent_and_non_executable():
    assert CONTRACT.network_silent_default is True
    assert CONTRACT.live_execution_enabled is False
    assert CONTRACT.default_request_budget == 0
    assert CONTRACT.default_execution_mode == "dry_run"
    assert "live_navigation_by_default" in CONTRACT.denied_actions
    assert CAPABILITIES["supports"] == list(CONTRACT.supported_capabilities)


def test_playwright_registry_entry_is_derived_from_validated_contract():
    assert get_adapter("playwright") == CONTRACT.as_dict()


@pytest.mark.parametrize(
    "change",
    [
        {"network_silent_default": False},
        {"live_execution_enabled": True},
        {"default_request_budget": 1},
        {"required_approvals": ("future_live_readiness_approval",)},
    ],
)
def test_playwright_contract_cannot_enable_live_execution(change):
    with pytest.raises(ValueError):
        replace(CONTRACT, **change)
