from __future__ import annotations

import json
import stat

import pytest
from cryptography.fernet import Fernet

from aotp.sensitive_vault import SensitiveVault, SensitiveVaultError


def _vault(tmp_path):
    return SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())


def test_sensitive_vault_encrypts_before_persistence_and_returns_handle(tmp_path):
    vault = _vault(tmp_path)
    raw = "api" + "_key=abcdefghi123456"
    handle = vault.store(raw, artifact_kind="token", purpose="synthetic campaign credential")
    assert handle.uri.startswith("vault://campaign-1/secret/token/")
    ciphertext = next((tmp_path / "vault" / "ciphertext").glob("*.fernet"))
    metadata = next((tmp_path / "vault" / "metadata").glob("*.json"))
    assert raw not in ciphertext.read_text(encoding="utf-8", errors="ignore")
    assert raw not in metadata.read_text(encoding="utf-8")
    assert vault.read_raw(handle).decode() == raw
    assert stat.S_IMODE(ciphertext.stat().st_mode) == 0o600
    assert stat.S_IMODE(metadata.stat().st_mode) == 0o600


def test_sensitive_vault_normal_evidence_references_handle_only(tmp_path):
    vault = _vault(tmp_path)
    handle = vault.store(
        "validation payload poc material",
        classification="poc_sensitive",
        artifact_kind="proof",
        purpose="build reproducible proof",
    )
    record = vault.handle_record(handle)
    encoded = json.dumps(record)
    assert handle.uri in encoded
    assert "validation payload" not in encoded
    assert record["classification"] == "poc_sensitive"


def test_sensitive_vault_refuses_public_and_do_not_store_material(tmp_path):
    vault = _vault(tmp_path)
    with pytest.raises(SensitiveVaultError, match="public material"):
        vault.store("ordinary public metadata", classification="public", artifact_kind="note", purpose="normal evidence")
    with pytest.raises(SensitiveVaultError, match="cannot be persisted"):
        vault.store("memory only do not store", artifact_kind="token", purpose="temporary")


def test_sensitive_vault_rejects_sensitive_metadata(tmp_path):
    vault = _vault(tmp_path)
    with pytest.raises(SensitiveVaultError, match="metadata"):
        vault.store(
            "api" + "_key=abcdefghi123456",
            artifact_kind="token",
            purpose="synthetic campaign credential",
            metadata={"note": "api" + "_key=abcdefghi123456"},
        )


def test_sensitive_vault_detects_ciphertext_tamper(tmp_path):
    vault = _vault(tmp_path)
    handle = vault.store("password=abcdefghi123456", artifact_kind="password", purpose="synthetic")
    ciphertext = next((tmp_path / "vault" / "ciphertext").glob("*.fernet"))
    ciphertext.write_text("tampered", encoding="utf-8")
    with pytest.raises(SensitiveVaultError, match="integrity"):
        vault.read_raw(handle)
