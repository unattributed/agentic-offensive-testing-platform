import pytest

from aotp.evidence import EvidenceManifest, write_manifest
from aotp.finding_candidate import (
    FindingCandidate,
    create_candidate,
    load_candidate,
    write_candidate,
)
from aotp.verifier import create_verification, write_verification


def test_candidate_requires_evidence():
    with pytest.raises(ValueError):
        FindingCandidate("id", "").validate()


def test_severity_confidence_and_evidence_strength_are_separate():
    finding = FindingCandidate("id", "evidence.json", severity_candidate="high", confidence="low", evidence_strength="medium")
    finding.validate()
    assert (finding.severity_candidate, finding.confidence, finding.evidence_strength) == ("high", "low", "medium")


def test_candidate_is_created_only_from_matching_fail_verdict(tmp_path):
    manifest = EvidenceManifest(
        run_id="candidate-run",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        operator="operator",
        sponsor_alias="program",
        target_alias="asset",
        authorization_reference="authorization-record",
        rules_of_engagement_reference="roe-record",
        confidentiality_reference=None,
        case_id="case-one",
        tool="test",
        verifier_verdict="inconclusive",
        confidence="low",
    )
    evidence_path = write_manifest(manifest, tmp_path / "evidence")
    verification = create_verification(
        verdict="fail",
        confidence="high",
        rationale="Recorded evidence failed the defined expectation.",
        evidence_manifest_sha256=manifest.manifest_sha256,
        evidence_references=["manifest:response_metadata"],
        verifier="human-reviewer",
    )
    verification_path = write_verification(
        verification, tmp_path / "evidence/verification.json"
    )
    candidate = create_candidate(
        evidence_path,
        verification_path,
        finding_id="finding-one",
        title="Observed control failure",
        summary="The recorded expectation failed and requires reproduction.",
        severity_candidate="medium",
        evidence_strength="medium",
    )
    path = write_candidate(candidate, tmp_path / "finding.json")
    loaded = load_candidate(path)
    assert loaded.state == "candidate"
    assert loaded.fingerprint
    assert loaded.target_alias == "asset"


def test_non_fail_verdict_cannot_create_candidate(tmp_path):
    manifest = EvidenceManifest(
        run_id="candidate-run",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        operator="operator",
        sponsor_alias="program",
        target_alias="asset",
        authorization_reference="authorization-record",
        rules_of_engagement_reference="roe-record",
        confidentiality_reference=None,
        case_id="case-one",
        tool="test",
        verifier_verdict="inconclusive",
        confidence="low",
    )
    evidence_path = write_manifest(manifest, tmp_path / "evidence")
    verification = create_verification(
        verdict="inconclusive",
        confidence="low",
        rationale="Evidence is not sufficient.",
        evidence_manifest_sha256=manifest.manifest_sha256,
        evidence_references=[],
        verifier="human-reviewer",
    )
    verification_path = write_verification(
        verification, tmp_path / "evidence/verification.json"
    )
    with pytest.raises(ValueError, match="only a fail verdict"):
        create_candidate(
            evidence_path,
            verification_path,
            finding_id="finding-one",
            title="Unsupported candidate",
            summary="This must not be created.",
        )
