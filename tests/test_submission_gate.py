from __future__ import annotations

import os

import pytest

from aotp.evidence import EvidenceManifest, write_manifest
from aotp.report_package import build_report_package, load_report_package
from aotp.submission_gate import (
    APPROVED_DECISION,
    SubmissionApproval,
    evaluate_submission_gate,
    load_submission_approval,
    write_submission_approval,
)


def _package(tmp_path):
    evidence = EvidenceManifest(
        run_id="submission-gate-run",
        timestamp_utc="2026-07-01T00:00:00+00:00",
        operator="operator-alias",
        sponsor_alias="sponsor-alias",
        target_alias="asset-alias",
        authorization_reference="authorization-reference",
        rules_of_engagement_reference="rules-reference",
        confidentiality_reference=None,
        case_id="case-alias",
        tool="network-silent-test",
        verifier_verdict="inconclusive",
        confidence="low",
    )
    evidence_path = write_manifest(evidence, tmp_path / "evidence")
    draft = tmp_path / "draft.md"
    draft.write_text("# Draft report\n", encoding="utf-8")
    package_path = build_report_package(
        draft,
        [evidence_path],
        tmp_path / "package",
        package_id="package-one",
        created_at_utc="2026-07-01T00:00:00Z",
    )
    return package_path, load_report_package(package_path)


def _approval(package_sha256, reviewer="human-reviewer"):
    return SubmissionApproval(
        decision_id="manual-review-one",
        report_package_sha256=package_sha256,
        reviewer_alias=reviewer,
        decision=APPROVED_DECISION,
        decided_at_utc="2026-07-01T00:00:00Z",
        rationale="Reviewed the draft and its evidence references.",
    )


def test_submission_gate_requires_explicit_human_approval(tmp_path):
    package_path, _ = _package(tmp_path)

    decision = evaluate_submission_gate(package_path, None)

    assert decision.allowed is False
    assert decision.status == "pending_human_review"


def test_submission_gate_allows_manual_operator_action_only(tmp_path):
    package_path, package = _package(tmp_path)
    approval = _approval(package.package_sha256)
    approval_path = write_submission_approval(
        approval, tmp_path / "submission-approval.json"
    )

    loaded = load_submission_approval(approval_path)
    decision = evaluate_submission_gate(package_path, loaded)

    assert decision.allowed is True
    assert decision.status == "approved_for_manual_submission"
    assert "manual operator submission only" in decision.reason
    assert os.stat(approval_path).st_mode & 0o777 == 0o600


@pytest.mark.parametrize("reviewer", ["system", "bot", "release-bot"])
def test_submission_gate_rejects_automation_reviewers(tmp_path, reviewer):
    _, package = _package(tmp_path)
    with pytest.raises(ValueError, match="named human reviewer"):
        _approval(package.package_sha256, reviewer=reviewer).validate()


def test_submission_gate_rejects_approval_for_another_package(tmp_path):
    package_path, _ = _package(tmp_path)

    decision = evaluate_submission_gate(package_path, _approval("f" * 64))

    assert decision.allowed is False
    assert decision.status == "denied"
