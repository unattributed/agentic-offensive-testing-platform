from aotp.evidence import EvidenceManifest, write_manifest
from aotp.finding_candidate import create_candidate, write_candidate
from aotp.finding_lifecycle import transition
from aotp.reporter import generate_markdown
from aotp.verifier import create_verification, write_verification


def test_report_uses_evidence_only(tmp_path):
    manifest = EvidenceManifest(
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
    write_manifest(manifest, tmp_path)
    report = generate_markdown(tmp_path)
    assert "case-one" in report
    assert "does not infer vulnerabilities" in report
    assert "critical vulnerability" not in report.lower()
    assert "No evidence-bound candidate" in report


def test_report_includes_only_human_validated_ready_candidate(tmp_path):
    evidence_root = tmp_path / "evidence"
    findings_root = tmp_path / "findings"
    manifest = EvidenceManifest(
        run_id="run-report",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        operator="operator",
        sponsor_alias="sponsor",
        target_alias="asset-one",
        authorization_reference="authorization-record",
        rules_of_engagement_reference="roe-record",
        confidentiality_reference=None,
        case_id="case-one",
        tool="test",
        verifier_verdict="inconclusive",
        confidence="low",
    )
    evidence_path = write_manifest(manifest, evidence_root)
    verification = create_verification(
        verdict="fail",
        confidence="high",
        rationale="Recorded evidence failed the defined expectation.",
        evidence_manifest_sha256=manifest.manifest_sha256,
        evidence_references=["manifest:response_metadata"],
        verifier="human-reviewer",
    )
    verification_path = write_verification(
        verification, evidence_root / "verification.json"
    )
    candidate = create_candidate(
        evidence_path,
        verification_path,
        finding_id="finding-ready",
        title="Recorded control failure",
        summary="The supplied evidence records the failed expectation.",
        severity_candidate="medium",
        evidence_strength="strong",
    )
    transition(candidate, "needs_human_review", reviewer="analyst")
    transition(candidate, "confirmed", reviewer="analyst", human_validated=True)
    transition(candidate, "ready_for_report", reviewer="analyst")
    write_candidate(candidate, findings_root / "finding-ready.json")

    report = generate_markdown(evidence_root, findings_root)
    assert "Recorded control failure" in report
    assert "Severity candidate: `medium`" in report
    assert "Report-ready findings: `1`" in report


def test_report_refuses_modified_evidence(tmp_path):
    path = write_manifest(
        EvidenceManifest(
            run_id="run-report",
            timestamp_utc="2026-01-01T00:00:00+00:00",
            operator="operator",
            sponsor_alias="sponsor",
            target_alias="asset-one",
            authorization_reference="authorization-record",
            rules_of_engagement_reference="roe-record",
            confidentiality_reference=None,
            case_id="case-one",
            tool="test",
            verifier_verdict="inconclusive",
            confidence="low",
        ),
        tmp_path,
    )
    path.write_text(path.read_text().replace("case-one", "changed-case"))
    import pytest

    with pytest.raises(ValueError, match="evidence verification failed"):
        generate_markdown(tmp_path)
