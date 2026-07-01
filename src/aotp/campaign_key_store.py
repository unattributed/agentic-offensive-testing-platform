"""Campaign-local key store for encrypted sensitive evidence."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from .evidence import sha256_file, utc_now


class CampaignKeyStoreError(ValueError):
    """Raised when campaign key storage is unsafe or unavailable."""


@dataclass(frozen=True)
class CampaignKeyRecord:
    campaign_id: str
    created_at_utc: str
    key_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "created_at_utc": self.created_at_utc,
            "key_sha256": self.key_sha256,
        }


class CampaignKeyStore:
    """Store Fernet keys under a private local directory with metadata only in reports."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        if self.root.exists() and self.root.is_symlink():
            raise CampaignKeyStoreError("campaign key root cannot be a symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)

    def key_path(self, campaign_id: str) -> Path:
        safe = _safe_campaign_id(campaign_id)
        return self.root / f"{safe}.fernet.key"

    def get_or_create_key(self, campaign_id: str) -> bytes:
        path = self.key_path(campaign_id)
        if path.exists():
            if path.is_symlink():
                raise CampaignKeyStoreError("campaign key path cannot be a symlink")
            key = path.read_bytes().strip()
            _validate_fernet_key(key)
            return key
        key = Fernet.generate_key()
        _atomic_write_bytes(path, key + b"\n")
        os.chmod(path, 0o600)
        return key

    def metadata(self, campaign_id: str) -> CampaignKeyRecord:
        path = self.key_path(campaign_id)
        if not path.is_file() or path.is_symlink():
            raise CampaignKeyStoreError("campaign key does not exist")
        return CampaignKeyRecord(
            campaign_id=_safe_campaign_id(campaign_id),
            created_at_utc=utc_now(),
            key_sha256=sha256_file(path),
        )


def _safe_campaign_id(campaign_id: str) -> str:
    if not isinstance(campaign_id, str) or not campaign_id:
        raise CampaignKeyStoreError("campaign_id is required")
    if any(character in campaign_id for character in "/\\ \t\n\r") or ".." in campaign_id:
        raise CampaignKeyStoreError("campaign_id is not safe for key storage")
    return campaign_id


def _validate_fernet_key(key: bytes) -> None:
    try:
        Fernet(key)
    except Exception as exc:  # pragma: no cover, cryptography chooses exact exception type
        raise CampaignKeyStoreError("campaign key is not a valid Fernet key") from exc


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
