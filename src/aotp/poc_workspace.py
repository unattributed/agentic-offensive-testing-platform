"""Classified PoC workspace for vault-backed proof material."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evidence import sha256_file, utc_now
from .vault_handles import VaultHandle, parse_vault_handle


_SAFE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class PocWorkspaceError(ValueError):
    """Raised when a PoC workspace operation is unsafe."""


@dataclass(frozen=True)
class PocWorkspace:
    root: Path
    campaign_id: str
    path: Path
    manifests: Path
    artifacts: Path

    @classmethod
    def create(cls, root: str | Path, *, campaign_id: str, workspace_id: str) -> "PocWorkspace":
        campaign = _safe(campaign_id, "campaign_id")
        workspace = _safe(workspace_id, "workspace_id")
        root_path = Path(root).expanduser().resolve()
        if root_path.exists() and root_path.is_symlink():
            raise PocWorkspaceError("PoC root cannot be a symlink")
        path = root_path / campaign / workspace
        manifests = path / "manifests"
        artifacts = path / "artifacts"
        for directory in (root_path, root_path / campaign, path, manifests, artifacts):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(directory, 0o700)
        return cls(root_path, campaign, path, manifests, artifacts)

    def write_manifest(
        self,
        *,
        name: str,
        handles: tuple[VaultHandle | str, ...],
        objective_id: str,
        reproduction_notes: tuple[str, ...],
    ) -> Path:
        safe_name = _safe(name, "name")
        parsed_handles = [parse_vault_handle(item) if isinstance(item, str) else item for item in handles]
        if any(handle.campaign_id != self.campaign_id for handle in parsed_handles):
            raise PocWorkspaceError("PoC handles must belong to the workspace campaign")
        record = {
            "schema_version": "1.0",
            "created_at_utc": utc_now(),
            "campaign_id": self.campaign_id,
            "objective_id": objective_id,
            "classification": "poc_sensitive",
            "vault_handles": [handle.uri for handle in parsed_handles],
            "reproduction_notes": list(reproduction_notes),
            "raw_material_policy": "vault_handles_only_no_plaintext",
        }
        path = self.manifests / f"{safe_name}.json"
        _atomic_write(path, json.dumps(record, indent=2, sort_keys=True) + "\n")
        os.chmod(path, 0o600)
        return path

    def manifest_hash(self, path: str | Path) -> str:
        candidate = Path(path).resolve()
        try:
            candidate.relative_to(self.manifests.resolve())
        except ValueError as exc:
            raise PocWorkspaceError("PoC manifest path escaped workspace") from exc
        return sha256_file(candidate)


def _safe(value: str, field: str) -> str:
    if not isinstance(value, str) or _SAFE.fullmatch(value) is None:
        raise PocWorkspaceError(f"{field} is not safe")
    return value


def _atomic_write(path: Path, payload: str) -> Path:
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
