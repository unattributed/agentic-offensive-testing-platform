"""Private, alias-only prior-testing memory."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .redaction import assert_value_redacted

SCHEMA_VERSION = "1.0"
REPORT_OUTCOMES = {
    "not_reported",
    "draft",
    "submitted_manually",
    "accepted",
    "rejected",
    "duplicate",
}
DUPLICATE_STATUSES = {
    "not_checked",
    "no_match",
    "possible_duplicate",
    "confirmed_duplicate",
}
_ALIAS = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class CampaignMemoryEntry:
    program_alias: str
    asset_alias: str
    test_type: str
    date_tested: str
    finding_fingerprints: tuple[str, ...]
    payload_family: str
    evidence_hash: str
    report_outcome: str
    duplicate_status: str
    schema_version: str = SCHEMA_VERSION

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported campaign memory schema")
        for field in ("program_alias", "asset_alias", "test_type", "payload_family"):
            value = getattr(self, field)
            if not isinstance(value, str) or not _ALIAS.fullmatch(value):
                raise ValueError(f"{field} must be an alias")
        try:
            date.fromisoformat(self.date_tested)
        except (TypeError, ValueError) as exc:
            raise ValueError("date_tested must be an ISO date") from exc
        if not isinstance(self.finding_fingerprints, tuple):
            raise ValueError("finding_fingerprints must be a tuple")
        if len(set(self.finding_fingerprints)) != len(self.finding_fingerprints):
            raise ValueError("finding_fingerprints must not contain duplicates")
        if any(not _SHA256.fullmatch(value) for value in self.finding_fingerprints):
            raise ValueError("finding fingerprints must be SHA256 values")
        if not _SHA256.fullmatch(self.evidence_hash):
            raise ValueError("evidence_hash must be a SHA256 value")
        if self.report_outcome not in REPORT_OUTCOMES:
            raise ValueError("report_outcome is unsupported")
        if self.duplicate_status not in DUPLICATE_STATUSES:
            raise ValueError("duplicate_status is unsupported")
        assert_value_redacted(asdict(self))


def finding_fingerprint(*, test_type: str, evidence_hash: str) -> str:
    """Build a stable fingerprint without target or finding prose."""
    if not _ALIAS.fullmatch(test_type):
        raise ValueError("test_type must be an alias")
    if not _SHA256.fullmatch(evidence_hash):
        raise ValueError("evidence_hash must be a SHA256 value")
    return hashlib.sha256(f"{test_type}:{evidence_hash}".encode()).hexdigest()


def duplicate_fingerprints(
    entries: Iterable[CampaignMemoryEntry],
    *,
    asset_alias: str,
    test_type: str,
    fingerprints: Iterable[str],
) -> tuple[str, ...]:
    """Return exact prior fingerprint matches for the same alias and test type."""
    if not _ALIAS.fullmatch(asset_alias):
        raise ValueError("asset_alias must be an alias")
    if not _ALIAS.fullmatch(test_type):
        raise ValueError("test_type must be an alias")
    requested = set(fingerprints)
    if any(not _SHA256.fullmatch(value) for value in requested):
        raise ValueError("fingerprints must be SHA256 values")
    matched: set[str] = set()
    for entry in entries:
        entry.validate()
        if entry.asset_alias == asset_alias and entry.test_type == test_type:
            matched.update(requested & set(entry.finding_fingerprints))
    return tuple(sorted(matched))


def write_campaign_memory(
    entries: Iterable[CampaignMemoryEntry], path: str | Path
) -> Path:
    validated = list(entries)
    for entry in validated:
        entry.validate()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "data_classification": "private",
        "entries": [asdict(entry) for entry in validated],
    }
    assert_value_redacted(payload)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".campaign-memory.", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
        os.chmod(output, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def load_campaign_memory(path: str | Path) -> tuple[CampaignMemoryEntry, ...]:
    try:
        payload: Any = json.loads(Path(path).read_text(encoding="utf-8"))
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != SCHEMA_VERSION
            or payload.get("data_classification") != "private"
            or not isinstance(payload.get("entries"), list)
        ):
            raise ValueError("campaign memory envelope is invalid")
        entries = tuple(
            CampaignMemoryEntry(
                **{
                    **item,
                    "finding_fingerprints": tuple(item["finding_fingerprints"]),
                }
            )
            for item in payload["entries"]
        )
        for entry in entries:
            entry.validate()
        return entries
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"campaign memory is invalid: {path}: {exc}") from exc
