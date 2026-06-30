from __future__ import annotations

from pathlib import Path

import pytest

from aotp.evidence import EvidenceManifest, register_artifact, write_manifest
from aotp.finding_candidate import create_candidate, write_candidate
from aotp.finding_lifecycle import transition
from aotp.report_review import (
    evaluate_report_review_gate,
    manifest_requires_report_review,
    report_inclusion_allowed,
)
from aotp.reporter import generate_markdown
from aotp.verifier import create_verification, write_verification


def _write_manifest(tmp_path: Path, *, panel: bool = True) -> tuple[Path, EvidenceManifest]:
    evidence_dir = tmp_path / ("panel-evidence" if panel else "web-evidence")
    evidence_dir.mkdir(parents=True)
    manifest = EvidenceManifest(
        run_id="review-gate-run",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        operator="example-operator",
        sponsor_alias="example-sponsor",
        target_alias="local-placeholder",
        authorization_reference="example-only",
        rules_of_engagement_reference="example-only",
        confidentiality_reference=None,
        case_id="control-panel-evidence-records" if panel else "web-case",
        tool="control-panel-dry-run-planner" if panel else "deterministic-dry-run",
        verifier_verdict="fail",
        confidence="medium",
        module_name="service_control_panel" if panel else "wstg_web_application",
        target_category="generic_management_interface" if panel else "web_application",
        execution_mode="dry_run",
        policy_decision="allowed",
        request_count=0,
        response_metadata=(
            {"observation_plan": {"network_silent": True, "request_count": 0}}
            if panel
            else {"status": "planned only"}
        ),
    )
    if panel:
        artifact = evidence_dir / "panel-evidence.json"
        artifact.write_text('{"schema_version":"1.0","network_silent":true}\n', encoding="utf-8")
        register_artifact(
            manifest,
            evidence_dir,
            artifact,
            role="service_control_panel_evidence_record",
            artifact_id="panel-evidence-record",
            redaction_status="passed",
        )
    path = write_manifest(manifest, evidence_dir)
    return path, manifest


def _write_fail_verification(manifest: EvidenceManifest, evidence_path: Path) -> Path:
    verification = create_verification(
        verdict="fail",
        confidence="medium",
        rationale="review gate test fixture",
        evidence_manifest_sha256=manifest.manifest_sha256 or "",
        evidence_references=["panel-evidence-record"],
        verifier="human-review-test",
    )
    return write_verification(verification, evidence_path.parent / "verification.json")


def test_panel_evidence_requires_explicit_candidate_review(tmp_path):
    evidence_path, manifest = _write_manifest(tmp_path, panel=True)
    verification_path = _write_fail_verification(manifest, evidence_path)

    gate = evaluate_report_review_gate(manifest)
    assert gate.review_required is True
    assert gate.allowed is False
    assert gate.status == "excluded_pending_review"

    with pytest.raises(ValueError, match="explicit human review"):
        create_candidate(
            evidence_path,
            verification_path,
            finding_id="panel-review-required",
            title="Panel review required",
            summary="This should not become a candidate without review.",
            severity_candidate="low",
            evidence_strength="medium",
        )


def test_panel_candidate_creation_requires_named_human_reviewer(tmp_path):
    evidence_path, manifest = _write_manifest(tmp_path, panel=True)
    verification_path = _write_fail_verification(manifest, evidence_path)

    with pytest.raises(ValueError, match="named human reviewer"):
        create_candidate(
            evidence_path,
            verification_path,
            finding_id="panel-review-system",
            title="Panel review requires reviewer",
            summary="System review is not accepted for panel promotion.",
            severity_candidate="low",
            evidence_strength="medium",
            report_reviewed=True,
            reviewer="system",
        )


def test_panel_candidate_can_be_created_after_explicit_review(tmp_path):
    evidence_path, manifest = _write_manifest(tmp_path, panel=True)
    verification_path = _write_fail_verification(manifest, evidence_path)

    candidate = create_candidate(
        evidence_path,
        verification_path,
        finding_id="panel-reviewed",
        title="Reviewed panel observation",
        summary="A human reviewed the panel evidence before candidate creation.",
        severity_candidate="low",
        evidence_strength="medium",
        report_reviewed=True,
        reviewer="human-reviewer",
    )

    assert candidate.state == "candidate"
    assert candidate.report_review_required is True
    assert candidate.report_review_status == "candidate_reviewed"
    assert candidate.report_reviewer == "human-reviewer"
    assert not report_inclusion_allowed(candidate)


def test_non_panel_evidence_does_not_require_report_review(tmp_path):
    evidence_path, manifest = _write_manifest(tmp_path, panel=False)
    verification_path = _write_fail_verification(manifest, evidence_path)

    gate = evaluate_report_review_gate(manifest)
    assert manifest_requires_report_review(manifest) is False
    assert gate.allowed is True
    candidate = create_candidate(
        evidence_path,
        verification_path,
        finding_id="web-reviewed",
        title="Web observation",
        summary="Non-panel evidence follows the existing finding candidate path.",
        severity_candidate="low",
        evidence_strength="medium",
    )
    assert candidate.report_review_required is False
    assert report_inclusion_allowed(candidate) is True


def test_report_excludes_panel_candidate_until_ready_for_report(tmp_path):
    evidence_path, manifest = _write_manifest(tmp_path, panel=True)
    verification_path = _write_fail_verification(manifest, evidence_path)
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    finding_path = findings_dir / "panel-reviewed.json"
    candidate = create_candidate(
        evidence_path,
        verification_path,
        finding_id="panel-reviewed",
        title="Reviewed panel observation",
        summary="A human reviewed the panel evidence before candidate creation.",
        severity_candidate="low",
        evidence_strength="medium",
        report_reviewed=True,
        reviewer="human-reviewer",
    )
    write_candidate(candidate, finding_path)

    draft = generate_markdown(evidence_path.parent, findings_dir)
    assert "Report-ready findings: `0`" in draft
    assert "Excluded non-ready candidates: `1`" in draft

    transition(candidate, "needs_human_review", reviewer="human-reviewer")
    transition(candidate, "confirmed", reviewer="human-reviewer", human_validated=True)
    transition(candidate, "ready_for_report", reviewer="human-reviewer", human_validated=True)
    write_candidate(candidate, finding_path)

    draft = generate_markdown(evidence_path.parent, findings_dir)
    assert "Report-ready findings: `1`" in draft
    assert "Reviewed panel observation" in draft
    assert "Report review status: `candidate_reviewed`" in draft
