from __future__ import annotations

import pytest

from aotp.vault_handles import VaultHandle, VaultHandleError, assert_handle_only, parse_vault_handle


def test_vault_handle_round_trip_is_opaque():
    handle = VaultHandle(
        campaign_id="campaign-1",
        handle_id="a" * 32,
        classification="secret",
        artifact_kind="token",
    )
    parsed = parse_vault_handle(handle.uri)
    assert parsed == handle
    assert parsed.as_dict()["uri"] == handle.uri
    assert_handle_only(handle.uri)


def test_vault_handle_rejects_plaintext_and_unsafe_components():
    with pytest.raises(VaultHandleError):
        parse_vault_handle("raw-secret-value")
    with pytest.raises(VaultHandleError):
        VaultHandle(
            campaign_id="../campaign",
            handle_id="a" * 32,
            classification="secret",
            artifact_kind="token",
        )
    with pytest.raises(VaultHandleError):
        VaultHandle(
            campaign_id="campaign-1",
            handle_id="not-hex",
            classification="secret",
            artifact_kind="token",
        )
