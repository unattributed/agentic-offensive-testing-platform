from aotp.evidence import EvidenceManifest, write_manifest
from aotp.reporter import generate_markdown


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
