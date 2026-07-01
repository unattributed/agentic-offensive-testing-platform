from __future__ import annotations

from dataclasses import replace

import pytest

from aotp.adapters.zap_adapter import CAPABILITIES, CONTRACT
from aotp.capability_registry import get_adapter


def test_zap_contract_limits_capabilities_and_declares_spider_boundaries():
    assert CONTRACT.supported_capabilities == (
        "passive_scan_placeholder",
        "limited_spider_placeholder",
    )
    assert {"rate_limits", "spider_limits", "allowed_urls"}.issubset(
        CONTRACT.required_scope_fields
    )
    assert "explicit_spider_approval" in CONTRACT.required_approvals
    assert "passive_metadata_only_by_default" in CONTRACT.required_evidence_handling


def test_zap_contract_denies_active_or_unscoped_scanning():
    assert {
        "active_scan_by_default",
        "active_scan_without_approval",
        "destructive_payloads",
        "unscoped_spider",
    }.issubset(CONTRACT.denied_actions)
    assert CONTRACT.live_execution_enabled is False
    assert CONTRACT.default_request_budget == 0
    assert CAPABILITIES["denies"] == list(CONTRACT.denied_actions)


def test_zap_registry_entry_is_derived_from_validated_contract():
    assert get_adapter("zap") == CONTRACT.as_dict()


@pytest.mark.parametrize(
    "change",
    [
        {"network_silent_default": False},
        {"live_execution_enabled": True},
        {"default_request_budget": 1},
        {"required_approvals": ("explicit_spider_approval",)},
    ],
)
def test_zap_contract_cannot_enable_scanning(change):
    with pytest.raises(ValueError):
        replace(CONTRACT, **change)
