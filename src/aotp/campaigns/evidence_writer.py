"""Deterministic evidence writer for generic WSTG live campaigns."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class CampaignEvidenceError(ValueError):
    """Raised when campaign evidence output is unsafe."""


@dataclass
class CampaignEvidenceWriter:
    """Write normalized JSON and Markdown artifacts with a SHA256 manifest."""

    root: Path | str
    artifacts: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        root = Path(self.root).expanduser().resolve()
        if root.exists() and root.is_symlink():
            raise CampaignEvidenceError("evidence root cannot be a symlink")
        root.mkdir(parents=True, exist_ok=True)
        self.root = root

    def write_json(self, relative: str, payload: Any) -> str:
        path = self._safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        self.artifacts[relative] = _sha256_file(path)
        return relative

    def write_jsonl(self, relative: str, rows: list[dict[str, Any]]) -> str:
        path = self._safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows), encoding="utf-8")
        self.artifacts[relative] = _sha256_file(path)
        return relative

    def write_text(self, relative: str, payload: str) -> str:
        path = self._safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        self.artifacts[relative] = _sha256_file(path)
        return relative

    def write_sha256s(self) -> str:
        sha_path = self._safe_path("SHA256SUMS")
        lines = []
        for path in sorted(p for p in self.root.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
            relative = str(path.relative_to(self.root))
            digest = _sha256_file(path)
            self.artifacts[relative] = digest
            lines.append(f"{digest}  {relative}\n")
        sha_path.write_text("".join(lines), encoding="utf-8")
        self.artifacts["SHA256SUMS"] = _sha256_file(sha_path)
        return "SHA256SUMS"

    def _safe_path(self, relative: str) -> Path:
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise CampaignEvidenceError("evidence path must be relative and cannot escape the root")
        path = (self.root / relative).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise CampaignEvidenceError("evidence path escaped the root") from exc
        return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
