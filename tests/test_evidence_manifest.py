import json
import stat

import pytest

from aotp.evidence import (
    EvidenceManifest,
    load_manifest,
    register_artifact,
    sha256_file,
    verify_evidence_directory,
    write_manifest,
)


def make_manifest():
    return EvidenceManifest(
        run_id="run-1",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        operator="operator",
        sponsor_alias="sponsor",
        target_alias="asset-one",
        authorization_reference="authorization-record",
        rules_of_engagement_reference="roe-record",
        confidentiality_reference=None,
        case_id="case-one",
        tool="dry-run",
        verifier_verdict="inconclusive",
        confidence="low",
    )


def test_manifest_round_trip(tmp_path):
    path = write_manifest(make_manifest(), tmp_path)
    assert json.loads(path.read_text())["case_id"] == "case-one"
    assert load_manifest(path).manifest_sha256
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700
    assert verify_evidence_directory(tmp_path) == []


def test_artifact_hash_is_verified(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("placeholder")
    manifest = make_manifest()
    manifest.sha256_hashes = {"artifact.txt": sha256_file(artifact)}
    write_manifest(manifest, tmp_path)
    assert verify_evidence_directory(tmp_path) == []


def test_manifest_integrity_detects_changed_fields(tmp_path):
    path = write_manifest(make_manifest(), tmp_path)
    data = json.loads(path.read_text())
    data["case_id"] = "changed"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="integrity check failed"):
        load_manifest(path)


def test_manifest_rejects_invalid_required_fields():
    manifest = make_manifest()
    manifest.request_count = -1
    with pytest.raises(ValueError, match="request_count"):
        manifest.validate()


def test_registered_artifact_is_verified_and_modification_is_detected(tmp_path):
    artifact = tmp_path / "response.txt"
    artifact.write_text("synthetic response metadata", encoding="utf-8")
    manifest = make_manifest()
    record = register_artifact(
        manifest,
        tmp_path,
        "response.txt",
        role="response_metadata",
        artifact_id="response-1",
    )
    assert record["raw_sha256"] == record["redacted_sha256"]
    write_manifest(manifest, tmp_path)
    assert verify_evidence_directory(tmp_path) == []
    artifact.write_text("modified", encoding="utf-8")
    assert verify_evidence_directory(tmp_path) == [
        "artifact verification failed: response.txt"
    ]


def test_artifact_registration_rejects_escape_and_symlink(tmp_path):
    outside = tmp_path.parent / "outside-artifact.txt"
    outside.write_text("outside", encoding="utf-8")
    with pytest.raises(ValueError, match="outside evidence"):
        register_artifact(
            make_manifest(),
            tmp_path,
            outside,
            role="invalid",
            artifact_id="outside",
        )
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="non-symlink"):
        register_artifact(
            make_manifest(),
            tmp_path,
            link,
            role="invalid",
            artifact_id="link",
        )

# SPRINT4_HEADER_EVIDENCE_TESTS
from aotp.wstg_case_registry import build_dry_run_record


def test_wstg_header_evidence_record_contains_required_fields():
    record = build_dry_run_record("wstg-security-header-review")
    assert record["case_id"] == "wstg-security-header-review"
    assert record["module"] == "wstg_web_application"
    assert record["target_alias"] == "example-target"
    assert record["policy_decision"] == "allowed_dry_run"
    assert record["execution_mode"] == "dry_run"
    assert record["request_count"] == 0
    assert record["verifier_verdict"] == "manual_review"
    assert record["confidence"] == "not_assessed"
    assert record["artifact_placeholders"]
    assert record["redaction_status"] == "placeholder_only_no_private_material"
