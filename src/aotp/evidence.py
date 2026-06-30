"""Structured evidence manifests and artifact hashing."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import mimetypes
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .redaction import assert_redacted, assert_value_redacted
from .verifier import Verdict


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class EvidenceManifest:
    run_id: str
    timestamp_utc: str
    operator: str
    sponsor_alias: str
    target_alias: str
    authorization_reference: str
    rules_of_engagement_reference: str
    confidentiality_reference: str | None
    case_id: str
    tool: str
    verifier_verdict: str
    confidence: str
    campaign_id: str | None = None
    campaign_iteration_id: str | None = None
    parent_test_objective: str | None = None
    module_name: str | None = None
    wstg_mapping: list[str] = field(default_factory=list)
    artifact_mapping: list[str] = field(default_factory=list)
    target_category: str = "placeholder"
    execution_mode: str = "dry_run"
    policy_decision: str = "allowed"
    request_count: int = 0
    request_metadata: dict[str, Any] = field(default_factory=dict)
    response_metadata: dict[str, Any] = field(default_factory=dict)
    screenshots: list[str] = field(default_factory=list)
    dom_snapshot: str | None = None
    proxy_capture: str | None = None
    fuzzing_corpus_reference: str | None = None
    sbom_artifact: str | None = None
    configuration_artifact: str | None = None
    cryptographic_evidence: str | None = None
    raw_evidence_hash: str | None = None
    redacted_evidence_hash: str | None = None
    finding_candidate_id: str | None = None
    report_inclusion_status: str = "excluded_pending_review"
    redaction_status: str = "passed"
    sha256_hashes: dict[str, str] = field(default_factory=dict)
    schema_version: str = "1.0"
    manifest_sha256: str | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    def validate(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported evidence schema version")
        if self.verifier_verdict not in set(Verdict):
            raise ValueError("unsupported verifier verdict")
        required = {
            "run_id": self.run_id,
            "timestamp_utc": self.timestamp_utc,
            "operator": self.operator,
            "sponsor_alias": self.sponsor_alias,
            "target_alias": self.target_alias,
            "authorization_reference": self.authorization_reference,
            "rules_of_engagement_reference": self.rules_of_engagement_reference,
            "case_id": self.case_id,
            "tool": self.tool,
            "confidence": self.confidence,
        }
        missing = [name for name, value in required.items() if not isinstance(value, str) or not value]
        if missing:
            raise ValueError("required evidence fields are missing: " + ", ".join(missing))
        try:
            timestamp = datetime.fromisoformat(self.timestamp_utc.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("evidence timestamp is invalid") from exc
        if timestamp.tzinfo is None:
            raise ValueError("evidence timestamp must include a timezone")
        if not isinstance(self.request_count, int) or isinstance(self.request_count, bool) or self.request_count < 0:
            raise ValueError("request_count must be a non-negative integer")
        if self.confidence not in {"not_assessed", "low", "medium", "high"}:
            raise ValueError("unsupported evidence confidence")
        if self.execution_mode not in {"dry_run", "live_stub", "not_executed", "live"}:
            raise ValueError("unsupported evidence execution mode")
        if self.report_inclusion_status not in {
            "excluded_pending_review",
            "excluded",
            "candidate",
            "included",
        }:
            raise ValueError("unsupported report inclusion status")
        for relative, digest in self.sha256_hashes.items():
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("artifact hash paths must remain relative to evidence directory")
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ValueError("artifact hashes must be lowercase SHA256 digests")
        for index, artifact in enumerate(self.artifacts):
            if not isinstance(artifact, dict):
                raise ValueError(f"artifacts[{index}] must be a mapping")
            required_artifact = {
                "artifact_id",
                "role",
                "path",
                "redacted_path",
                "media_type",
                "size_bytes",
                "raw_sha256",
                "redacted_sha256",
                "redaction_status",
            }
            if set(artifact) != required_artifact:
                raise ValueError(f"artifacts[{index}] fields are invalid")
            for path_field in ("path", "redacted_path"):
                artifact_path = Path(str(artifact[path_field]))
                if artifact_path.is_absolute() or ".." in artifact_path.parts:
                    raise ValueError("artifact paths must remain relative to evidence directory")
            if not isinstance(artifact["size_bytes"], int) or artifact["size_bytes"] < 0:
                raise ValueError("artifact size must be a non-negative integer")
            for hash_field in ("raw_sha256", "redacted_sha256"):
                digest = artifact[hash_field]
                if len(digest) != 64 or any(
                    character not in "0123456789abcdef" for character in digest
                ):
                    raise ValueError("artifact hashes must be lowercase SHA256 digests")
        encoded = json.dumps(asdict(self), sort_keys=True)
        assert_redacted(encoded)
        assert_value_redacted(asdict(self))
        if self.redaction_status != "passed":
            raise ValueError("evidence redaction did not pass")
        if self.manifest_sha256 is not None and self.manifest_sha256 != manifest_digest(self):
            raise ValueError("evidence manifest integrity check failed")


def manifest_digest(manifest: EvidenceManifest) -> str:
    payload = asdict(manifest)
    payload["manifest_sha256"] = None
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def write_manifest(manifest: EvidenceManifest, directory: str | Path) -> Path:
    manifest.manifest_sha256 = None
    manifest.validate()
    manifest.manifest_sha256 = manifest_digest(manifest)
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    os.chmod(output, 0o700)
    path = output / "evidence.json"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".evidence.", suffix=".tmp", dir=output)
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


def load_manifest(path: str | Path) -> EvidenceManifest:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        manifest = EvidenceManifest(**data)
        manifest.validate()
        return manifest
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"evidence manifest is invalid: {path}: {exc}") from exc


def register_artifact(
    manifest: EvidenceManifest,
    evidence_directory: str | Path,
    artifact_path: str | Path,
    *,
    role: str,
    artifact_id: str,
    redacted_path: str | Path | None = None,
    redaction_status: str = "not_required",
) -> dict[str, Any]:
    root = Path(evidence_directory).resolve()
    raw_candidate = Path(artifact_path)
    raw_candidate = raw_candidate if raw_candidate.is_absolute() else root / raw_candidate
    if raw_candidate.is_symlink():
        raise ValueError("artifact must be a regular non-symlink file")
    raw = raw_candidate.resolve()
    try:
        relative = raw.relative_to(root)
    except ValueError as exc:
        raise ValueError("artifact path is outside evidence directory") from exc
    if not raw.is_file():
        raise ValueError("artifact must be a regular non-symlink file")
    redacted = raw
    if redacted_path is not None:
        redacted_candidate = Path(redacted_path)
        redacted_candidate = (
            redacted_candidate if redacted_candidate.is_absolute() else root / redacted_candidate
        )
        if redacted_candidate.is_symlink():
            raise ValueError("redacted artifact must be a regular non-symlink file")
        redacted = redacted_candidate.resolve()
        try:
            redacted.relative_to(root)
        except ValueError as exc:
            raise ValueError("redacted artifact path is outside evidence directory") from exc
        if not redacted.is_file():
            raise ValueError("redacted artifact must be a regular non-symlink file")
    record = {
        "artifact_id": artifact_id,
        "role": role,
        "path": relative.as_posix(),
        "redacted_path": redacted.relative_to(root).as_posix(),
        "media_type": mimetypes.guess_type(raw.name)[0] or "application/octet-stream",
        "size_bytes": raw.stat().st_size,
        "raw_sha256": sha256_file(raw),
        "redacted_sha256": sha256_file(redacted),
        "redaction_status": redaction_status,
    }
    if any(item["artifact_id"] == artifact_id for item in manifest.artifacts):
        raise ValueError(f"duplicate artifact id: {artifact_id}")
    manifest.artifacts.append(record)
    return record


def verify_evidence_directory(directory: str | Path) -> list[str]:
    root = Path(directory)
    failures: list[str] = []
    paths = sorted(root.rglob("evidence.json")) if root.is_dir() else []
    if not paths:
        return ["no evidence manifests found"]
    for path in paths:
        try:
            manifest = load_manifest(path)
            for relative, expected in manifest.sha256_hashes.items():
                artifact = path.parent / relative
                if not artifact.is_file() or sha256_file(artifact) != expected:
                    failures.append(f"artifact hash mismatch: {relative}")
            for artifact in manifest.artifacts:
                artifact_path = (path.parent / artifact["path"]).resolve()
                try:
                    artifact_path.relative_to(path.parent.resolve())
                except ValueError:
                    failures.append(f"artifact path escapes evidence directory: {artifact['path']}")
                    continue
                if (
                    not artifact_path.is_file()
                    or artifact_path.is_symlink()
                    or sha256_file(artifact_path) != artifact["raw_sha256"]
                    or artifact_path.stat().st_size != artifact["size_bytes"]
                ):
                    failures.append(f"artifact verification failed: {artifact['path']}")
                redacted_path = (path.parent / artifact["redacted_path"]).resolve()
                if artifact["redacted_path"] != artifact["path"] and (
                    not redacted_path.is_file()
                    or redacted_path.is_symlink()
                    or sha256_file(redacted_path) != artifact["redacted_sha256"]
                ):
                    failures.append(
                        f"redacted artifact verification failed: {artifact['redacted_path']}"
                    )
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"{path}: {exc}")
    return failures
