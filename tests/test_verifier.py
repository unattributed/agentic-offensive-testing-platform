import json

import pytest

from aotp.evidence import EvidenceManifest, write_manifest
from aotp.verifier import (
    create_verification,
    load_verification,
    write_verification,
)


def make_manifest():
    return EvidenceManifest(
        run_id="run-verifier",
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


def test_fail_verdict_requires_and_preserves_evidence_reference(tmp_path):
    manifest_path = write_manifest(make_manifest(), tmp_path)
    manifest = json.loads(manifest_path.read_text())
    result = create_verification(
        verdict="fail",
        confidence="high",
        rationale="Recorded response metadata did not match the approved expectation.",
        evidence_manifest_sha256=manifest["manifest_sha256"],
        evidence_references=["manifest:response_metadata"],
        verifier="human-reviewer",
    )
    path = write_verification(result, tmp_path / "verification.json")
    loaded = load_verification(path)
    assert loaded.verdict == "fail"
    assert loaded.result_sha256


def test_pass_or_fail_without_evidence_is_denied(tmp_path):
    manifest_path = write_manifest(make_manifest(), tmp_path)
    manifest = json.loads(manifest_path.read_text())
    with pytest.raises(ValueError, match="require evidence references"):
        create_verification(
            verdict="pass",
            confidence="medium",
            rationale="No evidence reference supplied.",
            evidence_manifest_sha256=manifest["manifest_sha256"],
            evidence_references=[],
            verifier="human-reviewer",
        )


def test_unsupported_verdict_is_denied():
    with pytest.raises(ValueError, match="unsupported verifier verdict"):
        create_verification(
            verdict="vulnerable",
            confidence="high",
            rationale="Unsupported claim.",
            evidence_manifest_sha256="a" * 64,
            evidence_references=["manifest:test"],
            verifier="human-reviewer",
        )


def test_verification_integrity_detects_change(tmp_path):
    result = create_verification(
        verdict="inconclusive",
        confidence="low",
        rationale="More evidence is required.",
        evidence_manifest_sha256="a" * 64,
        evidence_references=[],
        verifier="human-reviewer",
    )
    path = write_verification(result, tmp_path / "verification.json")
    data = json.loads(path.read_text())
    data["confidence"] = "high"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="integrity check failed"):
        load_verification(path)
