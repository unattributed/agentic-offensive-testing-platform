from __future__ import annotations

from dataclasses import replace

import pytest

from aotp.adapters.ai_browser_suite_adapter import CONTRACT as BROWSER_SUITE_CONTRACT
from aotp.adapters.mitmproxy_adapter import CONTRACT as MITMPROXY_CONTRACT
from aotp.adapters.osmap_adapter import CONTRACT as OSMAP_CONTRACT
from aotp.adapters.playwright_adapter import CONTRACT as PLAYWRIGHT_CONTRACT
from aotp.adapters.zap_adapter import CONTRACT as ZAP_CONTRACT


def test_all_adapter_contracts_share_the_fail_closed_baseline():
    for contract in (
        BROWSER_SUITE_CONTRACT,
        MITMPROXY_CONTRACT,
        OSMAP_CONTRACT,
        PLAYWRIGHT_CONTRACT,
        ZAP_CONTRACT,
    ):
        assert contract.network_silent_default is True
        assert contract.live_execution_enabled is False
        assert contract.default_request_budget == 0
        assert "explicit_private_scope" in contract.required_approvals
        assert "policy_gate_approval" in contract.required_approvals


@pytest.mark.parametrize(
    "change",
    [
        {"source_reference": "http://docs.example.invalid/adapter"},
        {"default_execution_mode": "live"},
        {"live_readiness_status": "ready"},
        {"optional_dependency_status": "required"},
        {
            "supported_capabilities": (
                "navigation_placeholder",
                "navigation_placeholder",
            )
        },
    ],
)
def test_adapter_contract_rejects_malformed_or_enabled_variants(change):
    with pytest.raises(ValueError):
        replace(PLAYWRIGHT_CONTRACT, **change)
