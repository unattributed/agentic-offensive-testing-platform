from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet

from aotp.poc_workspace import PocWorkspace, PocWorkspaceError
from aotp.sensitive_vault import SensitiveVault


def test_poc_workspace_records_vault_handles_without_plaintext(tmp_path):
    vault = SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())
    raw = "poc replay steps with password=abcdefghi123456"
    handle = vault.store(raw, classification="poc_sensitive", artifact_kind="proof", purpose="proof")
    workspace = PocWorkspace.create(tmp_path / "poc", campaign_id="campaign-1", workspace_id="proof-1")
    manifest_path = workspace.write_manifest(
        name="proof-manifest",
        handles=(handle,),
        objective_id="objective-1",
        reproduction_notes=("Use the vault handle during authorized review.",),
    )
    data = json.loads(manifest_path.read_text())
    assert data["classification"] == "poc_sensitive"
    assert data["vault_handles"] == [handle.uri]
    assert raw not in manifest_path.read_text()
    assert len(workspace.manifest_hash(manifest_path)) == 64


def test_poc_workspace_rejects_cross_campaign_handle(tmp_path):
    vault = SensitiveVault(tmp_path / "vault", campaign_id="campaign-1", key=Fernet.generate_key())
    handle = vault.store("poc material", classification="poc_sensitive", artifact_kind="proof", purpose="proof")
    workspace = PocWorkspace.create(tmp_path / "poc", campaign_id="campaign-2", workspace_id="proof-1")
    with pytest.raises(PocWorkspaceError, match="workspace campaign"):
        workspace.write_manifest(
            name="proof-manifest",
            handles=(handle,),
            objective_id="objective-1",
            reproduction_notes=("Denied.",),
        )
