"""External local evidence reference validation for browser-context placeholders."""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any

from .redaction import assert_value_redacted

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_REDACTION = {"redacted", "placeholder_only", "not_applicable_redacted_source"}
REFERENCE_FIELDS = {
    "alias",
    "relative_path",
    "sha256",
    "provenance",
    "source_project_or_adapter_contract",
    "redaction_status",
}


def _has_symlink_between(root: Path, target: Path) -> bool:
    root = root.resolve()
    current = root
    rel_parts = target.resolve().relative_to(root).parts if target.exists() else target.relative_to(root).parts
    for part in rel_parts:
        current = current / part
        if current.exists() and current.is_symlink():
            return True
    return False


def validate_external_evidence_reference(reference: dict[str, Any], evidence_root: str | Path) -> dict[str, Any]:
    if not isinstance(reference, dict):
        raise ValueError("external evidence reference must be a mapping")
    unknown = sorted(set(reference) - REFERENCE_FIELDS)
    if unknown:
        raise ValueError(
            "external evidence reference contains unknown fields: " + ", ".join(unknown)
        )
    required = ["alias", "relative_path", "sha256", "provenance", "source_project_or_adapter_contract", "redaction_status"]
    missing = [field for field in required if not reference.get(field)]
    if missing:
        raise ValueError("missing external evidence reference fields: " + ", ".join(missing))
    digest = str(reference["sha256"])
    if not SHA256_RE.match(digest):
        raise ValueError("external evidence reference sha256 must be lowercase hex")
    if reference["redaction_status"] not in ALLOWED_REDACTION:
        raise ValueError("external evidence reference redaction status is not allowed")
    rel = PurePosixPath(str(reference["relative_path"]))
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("external evidence reference path must be relative and must not escape")
    root = Path(evidence_root).resolve()
    target = (root / Path(*rel.parts)).resolve()
    if root != target and root not in target.parents:
        raise ValueError("external evidence reference escapes evidence root")
    if target.exists() and target.is_symlink():
        raise ValueError("external evidence reference must not be a symlink")
    if target.exists() and _has_symlink_between(root, target):
        raise ValueError("external evidence reference path contains a symlink")
    result = {
        "alias": str(reference["alias"]),
        "relative_path": str(rel),
        "sha256": digest,
        "provenance": str(reference["provenance"]),
        "source_project_or_adapter_contract": str(reference["source_project_or_adapter_contract"]),
        "redaction_status": str(reference["redaction_status"]),
    }
    assert_value_redacted(result)
    return result
