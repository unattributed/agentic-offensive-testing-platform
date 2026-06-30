from __future__ import annotations

from pathlib import Path
import json

import pytest

from aotp.cli import main
from aotp.evidence import EvidenceManifest, register_artifact, write_manifest
from aotp.finding_candidate import FindingCandidate, create_candidate, write_candidate
from aotp.finding_lifecycle import transition
from aotp.panel_evidence import write_panel_evidence_record
from aotp.report_review import (
    PANEL_REVIEW_DECISION,
    PanelReportReviewDecision,
    evaluate_report_review_gate,
    manifest_requires_report_review,
    report_inclusion_allowed,
    load_report_review_decision,
    write_report_review_decision,
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
        response_metadata={"status": "planned only"},
    )
    if panel:
        case = {
            "id": manifest.case_id,
            "module": "service_control_panel",
            "category": "service_control_panel",
            "target_alias": manifest.target_alias,
            "target_category": manifest.target_category,
            "panel_alias": "example-admin-panel",
            "panel_type": "admin_panel",
            "safe_observation_only": True,
            "requested_observations": ["response_header_metadata"],
        }
        observation_plan = {
            "panel_alias": "example-admin-panel",
            "panel_type": "admin_panel",
            "target_alias": manifest.target_alias,
            "planned_observations": [
                {
                    "observation_id": "response_header_metadata",
                    "description": "placeholder",
                    "execution": "not_executed",
                    "evidence_placeholder": "response_header_metadata_placeholder",
                    "safety_boundary": "metadata placeholder only",
                }
            ],
            "network_silent": True,
            "request_count": 0,
            "credential_material": "not_collected",
            "screenshots": [],
            "captures": [],
            "finding_claims": [],
            "denied_runtime_behaviors": [],
        }
        manifest.response_metadata = {"observation_plan": observation_plan}
        artifact = write_panel_evidence_record(
            case,
            evidence_dir,
            policy_decision="allowed",
            execution_mode="dry_run",
            tool=manifest.tool,
            request_count=0,
            response_metadata=manifest.response_metadata,
        )
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


def _write_review(
    tmp_path: Path,
    manifest: EvidenceManifest,
    *,
    reviewer: str = "human-reviewer",
) -> Path:
    decision = PanelReportReviewDecision(
        decision_id="panel-review-decision",
        evidence_manifest_sha256=manifest.manifest_sha256 or "",
        reviewer_alias=reviewer,
        decision=PANEL_REVIEW_DECISION,
        decided_at_utc="2026-06-30T00:00:00Z",
        rationale="Reviewed captured panel fields for candidate promotion.",
    )
    return write_report_review_decision(decision, tmp_path / "panel-review.json")


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


@pytest.mark.parametrize("reviewer", ["system", "bot", "release-bot"])
def test_panel_candidate_creation_requires_named_human_reviewer(tmp_path, reviewer):
    evidence_path, manifest = _write_manifest(tmp_path, panel=True)

    with pytest.raises(ValueError, match="named human reviewer"):
        _write_review(tmp_path, manifest, reviewer=reviewer)


def test_panel_candidate_can_be_created_after_explicit_review(tmp_path):
    evidence_path, manifest = _write_manifest(tmp_path, panel=True)
    verification_path = _write_fail_verification(manifest, evidence_path)
    review_path = _write_review(tmp_path, manifest)

    candidate = create_candidate(
        evidence_path,
        verification_path,
        finding_id="panel-reviewed",
        title="Reviewed panel observation",
        summary="A human reviewed the panel evidence before candidate creation.",
        severity_candidate="low",
        evidence_strength="medium",
        report_review_path=review_path,
    )

    assert candidate.state == "candidate"
    assert candidate.report_review_required is True
    assert candidate.report_review_status == "candidate_reviewed"
    assert candidate.report_reviewer == "human-reviewer"
    assert candidate.report_review_reference == str(review_path)
    assert candidate.report_review_sha256
    assert not report_inclusion_allowed(candidate)


def test_panel_review_decision_must_match_exact_manifest(tmp_path):
    evidence_path, manifest = _write_manifest(tmp_path, panel=True)
    verification_path = _write_fail_verification(manifest, evidence_path)
    decision = PanelReportReviewDecision(
        decision_id="wrong-manifest-review",
        evidence_manifest_sha256="f" * 64,
        reviewer_alias="human-reviewer",
        decision=PANEL_REVIEW_DECISION,
        decided_at_utc="2026-06-30T00:00:00Z",
        rationale="This decision intentionally references another manifest.",
    )
    review_path = write_report_review_decision(decision, tmp_path / "wrong-review.json")
    with pytest.raises(ValueError, match="does not match"):
        create_candidate(
            evidence_path,
            verification_path,
            finding_id="wrong-review-binding",
            title="Wrong review binding",
            summary="This must be rejected.",
            severity_candidate="low",
            evidence_strength="medium",
            report_review_path=review_path,
        )


def test_cli_writes_manifest_bound_report_review_decision(tmp_path, capsys):
    evidence_path, manifest = _write_manifest(tmp_path, panel=True)
    output = tmp_path / "cli-panel-review.json"
    status = main(
        [
            "report-review-create",
            "--evidence",
            str(evidence_path),
            "--decision-id",
            "cli-panel-review",
            "--reviewer",
            "human-reviewer",
            "--rationale",
            "Reviewed the panel evidence artifact.",
            "--output",
            str(output),
        ]
    )
    assert status == 0
    response = json.loads(capsys.readouterr().out)
    assert response["evidence_manifest_sha256"] == manifest.manifest_sha256
    decision = load_report_review_decision(output)
    assert decision.reviewer_alias == "human-reviewer"
    assert decision.decision_sha256


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
    review_path = _write_review(tmp_path, manifest)
    candidate = create_candidate(
        evidence_path,
        verification_path,
        finding_id="panel-reviewed",
        title="Reviewed panel observation",
        summary="A human reviewed the panel evidence before candidate creation.",
        severity_candidate="low",
        evidence_strength="medium",
        report_review_path=review_path,
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
    assert "Captured service control panel fields" in draft


def test_report_rederives_panel_review_requirement_from_manifest(tmp_path):
    evidence_path, manifest = _write_manifest(tmp_path, panel=True)
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    candidate = FindingCandidate(
        finding_id="forged-panel-ready",
        evidence_reference=str(evidence_path),
        state="ready_for_report",
        severity_candidate="low",
        confidence="medium",
        evidence_strength="medium",
        human_validated=True,
        report_review_required=False,
        report_review_status="not_required",
        title="Forged panel inclusion",
        summary="This candidate must remain excluded.",
        evidence_manifest_sha256=manifest.manifest_sha256,
        verification_reference="missing-verification.json",
        verification_sha256="0" * 64,
        target_alias=manifest.target_alias,
        case_id=manifest.case_id,
        fingerprint="1" * 64,
    )
    write_candidate(candidate, findings_dir / "forged.json")

    draft = generate_markdown(evidence_path.parent, findings_dir)
    assert "Report-ready findings: `0`" in draft
    assert "Excluded non-ready candidates: `1`" in draft
    assert "Forged panel inclusion" not in draft
