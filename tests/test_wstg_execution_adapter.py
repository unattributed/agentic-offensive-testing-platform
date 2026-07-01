import pytest

from aotp.wstg.coverage import CoverageDisposition, CoverageTracker
from aotp.wstg.execution_adapter import (
    WSTGAdapterKind,
    WSTGEvidenceRole,
    WSTGExecutionAdapterError,
    WSTGExecutionResult,
    WSTGExecutionStatus,
    WSTGRedactedEvidenceArtifact,
    apply_execution_result_to_coverage,
    build_execution_request,
    create_finding_candidate,
)
from aotp.wstg.objective_generator import WSTGCampaignScope, generate_wstg_objectives
from aotp.wstg.strategy_map import ExecutableFamily, WSTGPhase, build_default_strategy_map


SAFE_DIGEST = "0" * 64


def _passive_objective():
    scope = WSTGCampaignScope(
        campaign_id="campaign-17-followup",
        target_alias="owned-app",
        base_url="https://example.test",
        authorization_reference="authz-17-followup",
        operator_approved=True,
        allowed_phases=frozenset({WSTGPhase.PASSIVE}),
        approved_families=frozenset({ExecutableFamily.HTTP_METADATA}),
    )
    return generate_wstg_objectives(scope, build_default_strategy_map())[0]


def _evidence(role=WSTGEvidenceRole.RESPONSE, reference="evidence/response-redacted.json"):
    return WSTGRedactedEvidenceArtifact(
        artifact_id="artifact-1",
        role=role,
        reference=reference,
        media_type="application/json",
        classification="restricted",
        raw_sha256=SAFE_DIGEST,
        redacted_sha256=SAFE_DIGEST,
    )


def _request():
    return build_execution_request(
        _passive_objective(),
        adapter_kind=WSTGAdapterKind.GOVERNED_TOOL,
        approval_reference="approval-17-followup",
        request_budget=1,
        execution_mode="live_stub",
    )


def test_execution_request_preserves_generated_objective_and_scope_arguments():
    request = _request()

    assert request.objective.wstg_id == "WSTG-v42-INFO-02"
    assert request.executor_name == "http_metadata"
    assert request.arguments["url"] == "https://example.test/"
    assert request.request_budget == 1


def test_redacted_evidence_rejects_absolute_or_unredacted_artifacts():
    with pytest.raises(WSTGExecutionAdapterError):
        WSTGRedactedEvidenceArtifact(
            artifact_id="bad",
            role=WSTGEvidenceRole.RESPONSE,
            reference="/tmp/raw.json",
            media_type="application/json",
            classification="restricted",
        )
    with pytest.raises(WSTGExecutionAdapterError):
        WSTGRedactedEvidenceArtifact(
            artifact_id="bad",
            role=WSTGEvidenceRole.RESPONSE,
            reference="evidence/raw.json",
            media_type="application/json",
            classification="restricted",
            redacted=False,
        )


def test_pass_fail_and_warning_results_convert_to_tested_coverage():
    tracker = CoverageTracker((_passive_objective(),))
    result = WSTGExecutionResult(
        request=_request(),
        status=WSTGExecutionStatus.PASS,
        summary="expected header metadata observed",
        evidence=(_evidence(),),
    )

    record = apply_execution_result_to_coverage(tracker, result)

    assert record.disposition is CoverageDisposition.TESTED
    assert record.evidence_references == ("evidence/response-redacted.json",)
    assert tracker.gap_summary()["statuses"]["tested"] == 1


def test_skip_and_not_applicable_results_update_coverage_with_reasons():
    skip_result = WSTGExecutionResult(
        request=_request(),
        status=WSTGExecutionStatus.SKIP,
        summary="adapter did not run",
        reasons=("tool dependency unavailable",),
    )
    na_result = WSTGExecutionResult(
        request=_request(),
        status=WSTGExecutionStatus.NOT_APPLICABLE,
        summary="objective does not apply to target",
        reasons=("target does not expose this surface",),
    )

    assert skip_result.coverage_disposition is CoverageDisposition.SKIPPED
    assert na_result.coverage_disposition is CoverageDisposition.SKIPPED
    assert "target does not expose" in na_result.coverage_reasons[0]


def test_finding_candidates_are_created_only_from_failed_results_with_evidence():
    failed = WSTGExecutionResult(
        request=_request(),
        status=WSTGExecutionStatus.FAIL,
        summary="security expectation was not met",
        evidence=(_evidence(reference="evidence/failure-redacted.json"),),
    )

    candidate = create_finding_candidate(
        failed,
        candidate_id="candidate-17-followup-1",
        title="WSTG evidence-backed observation",
        summary="Adapter evidence supports a candidate finding.",
        severity_candidate="low",
        confidence="medium",
    )
    result_with_candidate = WSTGExecutionResult(
        request=failed.request,
        status=failed.status,
        summary=failed.summary,
        evidence=failed.evidence,
        finding_candidate=candidate,
    )

    assert candidate.wstg_id == failed.request.objective.wstg_id
    assert result_with_candidate.finding_candidate is candidate

    passed = WSTGExecutionResult(
        request=_request(),
        status=WSTGExecutionStatus.PASS,
        summary="expected behavior observed",
        evidence=(_evidence(),),
    )
    with pytest.raises(WSTGExecutionAdapterError):
        create_finding_candidate(
            passed,
            candidate_id="candidate-17-followup-2",
            title="invalid",
            summary="invalid",
        )
