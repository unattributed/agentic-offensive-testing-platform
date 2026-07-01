"""Private bounded workspace for one agentic campaign run."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SAFE_COMPONENT = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class AgentWorkspaceError(ValueError):
    """Raised when a campaign workspace or artifact path is unsafe."""


def _safe_component(value: str, field: str) -> str:
    if not isinstance(value, str) or SAFE_COMPONENT.fullmatch(value) is None:
        raise AgentWorkspaceError(f"{field} must be a safe lowercase path component")
    return value


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class AgentCampaignWorkspace:
    root: Path
    program_alias: str
    run_id: str
    path: Path
    evidence: Path
    state: Path
    reports: Path

    @classmethod
    def create(
        cls,
        workspace_root: str | Path,
        *,
        program_alias: str,
        run_id: str,
    ) -> "AgentCampaignWorkspace":
        program = _safe_component(program_alias, "program_alias")
        run = _safe_component(run_id, "run_id")
        root_candidate = Path(workspace_root).expanduser()
        if root_candidate.exists() and root_candidate.is_symlink():
            raise AgentWorkspaceError("campaign workspace root cannot be a symlink")
        root = root_candidate.resolve()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
        path = root / program / run
        for directory in (root / program, path):
            if directory.exists() and directory.is_symlink():
                raise AgentWorkspaceError("campaign workspace cannot traverse a symlink")
            directory.mkdir(mode=0o700, exist_ok=True)
            os.chmod(directory, 0o700)
        if not _inside(path, root):
            raise AgentWorkspaceError("campaign workspace escaped its configured root")
        evidence = path / "evidence"
        state = path / "state"
        reports = path / "reports"
        for directory in (evidence, state, reports):
            directory.mkdir(mode=0o700, exist_ok=True)
            os.chmod(directory, 0o700)
        return cls(root, program, run, path, evidence, state, reports)

    def _destination(self, area: str, name: str, suffix: str) -> Path:
        safe_name = _safe_component(name, "artifact name")
        destinations = {
            "evidence": self.evidence,
            "state": self.state,
            "reports": self.reports,
        }
        if area not in destinations:
            raise AgentWorkspaceError("artifact area is not approved")
        destination = destinations[area] / f"{safe_name}{suffix}"
        if destination.exists() and destination.is_symlink():
            raise AgentWorkspaceError("artifact destination cannot be a symlink")
        if not _inside(destination, destinations[area]):
            raise AgentWorkspaceError("artifact path escaped its approved area")
        return destination

    @staticmethod
    def _atomic_write(path: Path, content: str) -> Path:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
            os.chmod(path, 0o600)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def write_json(self, area: str, name: str, value: dict[str, Any]) -> Path:
        return self._atomic_write(
            self._destination(area, name, ".json"),
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        )

    def write_text(self, area: str, name: str, value: str) -> Path:
        return self._atomic_write(self._destination(area, name, ".md"), value)
