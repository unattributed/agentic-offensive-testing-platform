import json

from aotp.evidence import EvidenceManifest, sha256_file, verify_evidence_directory, write_manifest


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
    assert verify_evidence_directory(tmp_path) == []


def test_artifact_hash_is_verified(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("placeholder")
    manifest = make_manifest()
    manifest.sha256_hashes = {"artifact.txt": sha256_file(artifact)}
    write_manifest(manifest, tmp_path)
    assert verify_evidence_directory(tmp_path) == []
