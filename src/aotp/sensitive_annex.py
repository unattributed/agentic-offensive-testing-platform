"""Sensitive annex export separated from normal reports."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from .evidence import sha256_file, utc_now
from .report_export_policy import SensitiveExportApproval, require_annex_export_approval
from .sensitive_vault import SensitiveVault
from .vault_handles import VaultHandle, parse_vault_handle


class SensitiveAnnexError(ValueError):
    """Raised when a sensitive annex cannot be exported safely."""


@dataclass(frozen=True)
class SensitiveAnnexResult:
    manifest_path: Path
    encrypted_annex_path: Path
    encrypted_annex_sha256: str
    manifest_sha256: str


def export_sensitive_annex(
    *,
    vault: SensitiveVault,
    handles: tuple[VaultHandle | str, ...],
    output_dir: str | Path,
    approval: SensitiveExportApproval,
    recipient_alias: str,
) -> SensitiveAnnexResult:
    require_annex_export_approval(campaign_id=vault.campaign_id, approval=approval)
    recipient = _safe_alias(recipient_alias)
    directory = Path(output_dir).expanduser().resolve()
    if directory.exists() and directory.is_symlink():
        raise SensitiveAnnexError("annex output directory cannot be a symlink")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    parsed = tuple(parse_vault_handle(item) if isinstance(item, str) else item for item in handles)
    records: list[dict[str, Any]] = []
    annex_items: list[dict[str, Any]] = []
    for handle in parsed:
        if handle.campaign_id != vault.campaign_id:
            raise SensitiveAnnexError("annex handle belongs to a different campaign")
        metadata = vault.metadata(handle)
        records.append(vault.handle_record(handle))
        annex_items.append(
            {
                "handle": handle.uri,
                "classification": metadata.classification,
                "artifact_kind": metadata.artifact_kind,
                "plaintext_sha256": metadata.plaintext_sha256,
                "plaintext_size_bytes": metadata.plaintext_size_bytes,
            }
        )
    annex_payload = {
        "schema_version": "1.0",
        "created_at_utc": utc_now(),
        "campaign_id": vault.campaign_id,
        "recipient_alias": recipient,
        "approval_id": approval.approval_id,
        "items": annex_items,
        "raw_material_policy": "encrypted_annex_contains_no_plaintext_export_by_default",
    }
    annex_key = Fernet.generate_key()
    encrypted = Fernet(annex_key).encrypt(json.dumps(annex_payload, sort_keys=True).encode("utf-8"))
    encrypted_path = directory / f"sensitive-annex-{vault.campaign_id}-{recipient}.fernet"
    _atomic_write_bytes(encrypted_path, encrypted)
    os.chmod(encrypted_path, 0o600)
    manifest = {
        "schema_version": "1.0",
        "created_at_utc": utc_now(),
        "campaign_id": vault.campaign_id,
        "recipient_alias": recipient,
        "approval": {
            "approval_id": approval.approval_id,
            "operator_alias": approval.operator_alias,
            "action": approval.action,
            "reason": approval.reason,
        },
        "encrypted_annex_path": encrypted_path.name,
        "encrypted_annex_sha256": sha256_file(encrypted_path),
        "annex_key_delivery": "manual_out_of_band_not_stored_in_manifest",
        "vault_records": records,
    }
    manifest_path = directory / f"sensitive-annex-{vault.campaign_id}-{recipient}.manifest.json"
    _atomic_write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.chmod(manifest_path, 0o600)
    return SensitiveAnnexResult(
        manifest_path=manifest_path,
        encrypted_annex_path=encrypted_path,
        encrypted_annex_sha256=sha256_file(encrypted_path),
        manifest_sha256=sha256_file(manifest_path),
    )


def _safe_alias(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise SensitiveAnnexError("recipient_alias is required")
    if any(character in value for character in "/\\ \t\n\r") or ".." in value:
        raise SensitiveAnnexError("recipient_alias is not safe")
    return value


def _atomic_write_bytes(path: Path, payload: bytes) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def _atomic_write_text(path: Path, payload: str) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path
