from __future__ import annotations

import stat

import pytest
from cryptography.fernet import Fernet

from aotp.campaign_key_store import CampaignKeyStore, CampaignKeyStoreError


def test_campaign_key_store_creates_private_fernet_key(tmp_path):
    store = CampaignKeyStore(tmp_path / "keys")
    key = store.get_or_create_key("campaign-1")
    assert store.get_or_create_key("campaign-1") == key
    Fernet(key)
    path = store.key_path("campaign-1")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    metadata = store.metadata("campaign-1")
    assert metadata.campaign_id == "campaign-1"
    assert len(metadata.key_sha256) == 64


def test_campaign_key_store_rejects_unsafe_campaign_id(tmp_path):
    store = CampaignKeyStore(tmp_path)
    with pytest.raises(CampaignKeyStoreError):
        store.get_or_create_key("../campaign")
