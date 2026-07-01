"""Human-reviewed draft report package construction."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .evidence import load_manifest, sha256_file
from .redaction import assert_redacted, assert_value_redacted

SCHEMA_VERSION = "1.0"
_ALIAS = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class ReportPackageManifest:
    package_id: str
    created_at_utc: str
    draft_report: str
    draft_report_sha256: str
    evidence_manifest_sha256: tuple[str, ...]
    status: str = "draft"
    human_review_required: bool = True
    review_status: str = "pending_human_review"
    submission_mode: str = "manual_only"
    schema_version: str = SCHEMA_VERSION
    package_sha256: str | None = None

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported report package schema")
        if not _ALIAS.fullmatch(self.package_id):
            raise ValueError("package_id must be an alias")
        try:
            created = datetime.fromisoformat(
                self.created_at_utc.replace("Z", "+00:00")
            )
        except (AttributeError, ValueError) as exc:
            raise ValueError("created_at_utc is invalid") from exc
        if created.tzinfo is None:
            raise ValueError("created_at_utc must include a timezone")
        if self.draft_report != "draft-report.md":
            raise ValueError("draft_report must use the package-local draft name")
        if not _SHA256.fullmatch(self.draft_report_sha256):
            raise ValueError("draft_report_sha256 is invalid")
        if not self.evidence_manifest_sha256:
            raise ValueError("report package requires evidence references")
        if len(set(self.evidence_manifest_sha256)) != len(
            self.evidence_manifest_sha256
        ):
            raise ValueError("evidence references must not contain duplicates")
        if any(
            not _SHA256.fullmatch(value)
            for value in self.evidence_manifest_sha256
        ):
            raise ValueError("evidence references must be SHA256 values")
        if (
            self.status != "draft"
            or not self.human_review_required
            or self.review_status != "pending_human_review"
            or self.submission_mode != "manual_only"
        ):
            raise ValueError("report package must remain a human-reviewed manual draft")
        assert_value_redacted(asdict(self))
        if self.package_sha256 is not None and self.package_sha256 != package_digest(
            self
        ):
            raise ValueError("report package integrity check failed")


def package_digest(manifest: ReportPackageManifest) -> str:
    payload = asdict(manifest)
    payload["package_sha256"] = None
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_report_package(
    draft_report: str | Path,
    evidence_manifests: Iterable[str | Path],
    output_directory: str | Path,
    *,
    package_id: str,
    created_at_utc: str | None = None,
) -> Path:
    source = Path(draft_report)
    if not source.is_file() or source.is_symlink():
        raise ValueError("draft report must be a regular non-symlink file")
    draft_text = source.read_text(encoding="utf-8")
    assert_redacted(draft_text)
    evidence_hashes: list[str] = []
    for path in evidence_manifests:
        manifest = load_manifest(path)
        if not manifest.manifest_sha256:
            raise ValueError("evidence manifest has no verified digest")
        evidence_hashes.append(manifest.manifest_sha256)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    os.chmod(output, 0o700)
    bundled_draft = output / "draft-report.md"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".draft-report.", dir=output
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(draft_text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, bundled_draft)
        os.chmod(bundled_draft, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    manifest = ReportPackageManifest(
        package_id=package_id,
        created_at_utc=created_at_utc or datetime.now(UTC).isoformat(),
        draft_report="draft-report.md",
        draft_report_sha256=sha256_file(bundled_draft),
        evidence_manifest_sha256=tuple(sorted(evidence_hashes)),
    )
    manifest.validate()
    manifest.package_sha256 = package_digest(manifest)
    path = output / "package-manifest.json"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".package-manifest.", dir=output
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(asdict(manifest), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def load_report_package(path: str | Path) -> ReportPackageManifest:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data["evidence_manifest_sha256"] = tuple(
            data["evidence_manifest_sha256"]
        )
        manifest = ReportPackageManifest(**data)
        manifest.validate()
        package_root = Path(path).parent
        draft = package_root / manifest.draft_report
        if (
            not draft.is_file()
            or draft.is_symlink()
            or sha256_file(draft) != manifest.draft_report_sha256
        ):
            raise ValueError("bundled draft integrity check failed")
        return manifest
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"report package is invalid: {path}: {exc}") from exc
