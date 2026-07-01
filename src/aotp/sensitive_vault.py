"""Encrypted campaign sensitive evidence vault."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from .evidence import sha256_file, utc_now
from .evidence_classifier import EvidenceClassification, EvidenceClassificationError, assert_may_store, classify_text, parse_classification
from .vault_handles import VaultHandle, parse_vault_handle


class SensitiveVaultError(ValueError):
    """Raised when sensitive vault operations are denied or invalid."""


@dataclass(frozen=True)
class VaultRecord:
    schema_version: str
    handle: VaultHandle
    created_at_utc: str
    classification: str
    artifact_kind: str
    purpose: str
    plaintext_sha256: str
    plaintext_size_bytes: int
    ciphertext_sha256: str
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "handle": self.handle.as_dict(),
            "created_at_utc": self.created_at_utc,
            "classification": self.classification,
            "artifact_kind": self.artifact_kind,
            "purpose": self.purpose,
            "plaintext_sha256": self.plaintext_sha256,
            "plaintext_size_bytes": self.plaintext_size_bytes,
            "ciphertext_sha256": self.ciphertext_sha256,
            "metadata": dict(self.metadata),
        }


class SensitiveVault:
    """Store raw sensitive evidence as Fernet-authenticated ciphertext plus safe metadata."""

    def __init__(self, root: str | Path, *, campaign_id: str, key: bytes) -> None:
        self.root = Path(root).expanduser().resolve()
        self.campaign_id = _safe_component(campaign_id, "campaign_id")
        self._fernet = Fernet(key)
        if self.root.exists() and self.root.is_symlink():
            raise SensitiveVaultError("sensitive vault root cannot be a symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        for directory in (self._cipher_dir, self._metadata_dir, self._logs_dir):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(directory, 0o700)

    @property
    def _cipher_dir(self) -> Path:
        return self.root / "ciphertext"

    @property
    def _metadata_dir(self) -> Path:
        return self.root / "metadata"

    @property
    def _logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def access_log_path(self) -> Path:
        return self._logs_dir / "raw-access.jsonl"

    def store(
        self,
        payload: bytes | str,
        *,
        classification: str | EvidenceClassification | None = None,
        artifact_kind: str,
        purpose: str,
        metadata: dict[str, Any] | None = None,
    ) -> VaultHandle:
        data = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)
        inferred = classify_text(data, context=f"{artifact_kind} {purpose}")
        chosen = parse_classification(classification) if classification is not None else inferred.classification
        try:
            assert_may_store(chosen)
        except EvidenceClassificationError as exc:
            raise SensitiveVaultError(str(exc)) from exc
        if chosen is EvidenceClassification.PUBLIC:
            raise SensitiveVaultError("public material belongs in normal evidence, not the sensitive vault")
        kind = _safe_component(artifact_kind, "artifact_kind")
        safe_metadata = _safe_metadata(metadata or {})
        handle = VaultHandle(
            campaign_id=self.campaign_id,
            handle_id=uuid.uuid4().hex,
            classification=chosen.value,
            artifact_kind=kind,
        )
        token = self._fernet.encrypt(data)
        cipher_path = self._cipher_path(handle)
        _atomic_write_bytes(cipher_path, token)
        os.chmod(cipher_path, 0o600)
        record = VaultRecord(
            schema_version="1.0",
            handle=handle,
            created_at_utc=utc_now(),
            classification=chosen.value,
            artifact_kind=kind,
            purpose=_safe_purpose(purpose),
            plaintext_sha256=hashlib.sha256(data).hexdigest(),
            plaintext_size_bytes=len(data),
            ciphertext_sha256=sha256_file(cipher_path),
            metadata=safe_metadata,
        )
        metadata_path = self._metadata_path(handle)
        _atomic_write_text(metadata_path, json.dumps(record.as_dict(), indent=2, sort_keys=True) + "\n")
        os.chmod(metadata_path, 0o600)
        return handle

    def metadata(self, handle: VaultHandle | str) -> VaultRecord:
        parsed = self._validate_handle(handle)
        path = self._metadata_path(parsed)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SensitiveVaultError("vault metadata cannot be read") from exc
        if data.get("schema_version") != "1.0":
            raise SensitiveVaultError("unsupported vault metadata schema")
        record_handle = parse_vault_handle(data["handle"]["uri"])
        if record_handle != parsed:
            raise SensitiveVaultError("vault metadata handle mismatch")
        return VaultRecord(
            schema_version=data["schema_version"],
            handle=record_handle,
            created_at_utc=data["created_at_utc"],
            classification=data["classification"],
            artifact_kind=data["artifact_kind"],
            purpose=data["purpose"],
            plaintext_sha256=data["plaintext_sha256"],
            plaintext_size_bytes=data["plaintext_size_bytes"],
            ciphertext_sha256=data["ciphertext_sha256"],
            metadata=dict(data.get("metadata", {})),
        )

    def read_raw(self, handle: VaultHandle | str) -> bytes:
        parsed = self._validate_handle(handle)
        cipher_path = self._cipher_path(parsed)
        metadata = self.metadata(parsed)
        if sha256_file(cipher_path) != metadata.ciphertext_sha256:
            raise SensitiveVaultError("vault ciphertext integrity check failed")
        try:
            payload = self._fernet.decrypt(cipher_path.read_bytes())
        except InvalidToken as exc:
            raise SensitiveVaultError("vault ciphertext authentication failed") from exc
        if hashlib.sha256(payload).hexdigest() != metadata.plaintext_sha256:
            raise SensitiveVaultError("vault plaintext digest mismatch")
        return payload

    def append_access_log(self, record: dict[str, Any]) -> Path:
        safe_record = _safe_metadata(record)
        safe_record.setdefault("schema_version", "1.0")
        safe_record.setdefault("timestamp_utc", utc_now())
        line = json.dumps(safe_record, sort_keys=True, allow_nan=False) + "\n"
        with self.access_log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        os.chmod(self.access_log_path, 0o600)
        return self.access_log_path

    def handle_record(self, handle: VaultHandle | str) -> dict[str, Any]:
        record = self.metadata(handle)
        return {
            "handle": record.handle.uri,
            "classification": record.classification,
            "artifact_kind": record.artifact_kind,
            "purpose": record.purpose,
            "plaintext_sha256": record.plaintext_sha256,
            "plaintext_size_bytes": record.plaintext_size_bytes,
            "ciphertext_sha256": record.ciphertext_sha256,
        }

    def _validate_handle(self, handle: VaultHandle | str) -> VaultHandle:
        parsed = parse_vault_handle(handle) if isinstance(handle, str) else handle
        if parsed.campaign_id != self.campaign_id:
            raise SensitiveVaultError("vault handle belongs to a different campaign")
        return parsed

    def _cipher_path(self, handle: VaultHandle) -> Path:
        return self._cipher_dir / f"{handle.handle_id}.fernet"

    def _metadata_path(self, handle: VaultHandle) -> Path:
        return self._metadata_dir / f"{handle.handle_id}.json"


def _safe_component(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise SensitiveVaultError(f"{field} is required")
    if any(character in value for character in "/\\ \t\n\r") or ".." in value:
        raise SensitiveVaultError(f"{field} is not safe")
    return value


def _safe_purpose(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SensitiveVaultError("purpose is required")
    if len(value) > 512:
        raise SensitiveVaultError("purpose is too long")
    return value.strip()


def _safe_metadata(value: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(value, sort_keys=True, default=str)
    if classify_text(encoded, context="vault metadata").vault_required:
        raise SensitiveVaultError("vault metadata cannot contain raw sensitive material")
    return json.loads(encoded)


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
