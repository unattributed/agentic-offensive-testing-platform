"""Structured evidence manifests and artifact hashing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .redaction import assert_redacted
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

    def validate(self) -> None:
        if self.verifier_verdict not in set(Verdict):
            raise ValueError("unsupported verifier verdict")
        encoded = json.dumps(asdict(self), sort_keys=True)
        assert_redacted(encoded)
        if self.redaction_status != "passed":
            raise ValueError("evidence redaction did not pass")


def write_manifest(manifest: EvidenceManifest, directory: str | Path) -> Path:
    manifest.validate()
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "evidence.json"
    path.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def verify_evidence_directory(directory: str | Path) -> list[str]:
    root = Path(directory)
    failures: list[str] = []
    paths = sorted(root.rglob("evidence.json")) if root.is_dir() else []
    if not paths:
        return ["no evidence manifests found"]
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            manifest = EvidenceManifest(**data)
            manifest.validate()
            for relative, expected in manifest.sha256_hashes.items():
                artifact = path.parent / relative
                if not artifact.is_file() or sha256_file(artifact) != expected:
                    failures.append(f"artifact hash mismatch: {relative}")
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"{path}: {exc}")
    return failures
