import json
import stat

import pytest

from aotp.evidence import EvidenceManifest, load_manifest, sha256_file, verify_evidence_directory, write_manifest


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
