from __future__ import annotations

from dataclasses import replace

import pytest

from aotp.adapters.mitmproxy_adapter import CAPABILITIES, CONTRACT
from aotp.capability_registry import get_adapter


def test_mitmproxy_contract_declares_scope_redaction_and_capture_authority():
    assert CONTRACT.supported_capabilities == (
        "authorized_local_capture_placeholder",
        "proxy_capture_placeholder",
    )
    assert "allowed_proxy_context" in CONTRACT.required_scope_fields
    assert "local_capture_authorization" in CONTRACT.required_approvals
    assert {
        "credential_stripping_required",
        "private_ca_material_excluded",
        "artifact_hash_required",
    }.issubset(CONTRACT.required_evidence_handling)


def test_mitmproxy_contract_denies_unscoped_or_secret_capture():
    assert {
        "credential_capture",
        "credential_persistence",
        "private_ca_material_commitment",
        "transparent_interception",
        "unscoped_interception",
    }.issubset(CONTRACT.denied_actions)
    assert CONTRACT.live_execution_enabled is False
    assert CONTRACT.default_request_budget == 0
    assert CAPABILITIES["denies"] == list(CONTRACT.denied_actions)


def test_mitmproxy_registry_entry_is_derived_from_validated_contract():
    assert get_adapter("mitmproxy") == CONTRACT.as_dict()


@pytest.mark.parametrize(
    "change",
    [
        {"network_silent_default": False},
        {"live_execution_enabled": True},
        {"default_request_budget": 1},
        {"required_approvals": ("local_capture_authorization",)},
    ],
)
def test_mitmproxy_contract_cannot_enable_interception(change):
    with pytest.raises(ValueError):
        replace(CONTRACT, **change)
