from __future__ import annotations

from pathlib import Path

from aotp.campaigns.execution_planner import CampaignAction
from aotp.campaigns.target_runtime import CampaignTargetRuntime, build_juice_shop_target_runtime
from aotp.campaigns.wstg_live_campaign import WSTGLiveCampaignConfig, WSTGLiveObservation, run_wstg_live_campaign


def _observation(action: CampaignAction, runtime: CampaignTargetRuntime, timeout: float) -> WSTGLiveObservation:
    assert timeout > 0
    url = runtime.normalized_base_url.rstrip("/") + action.path
    if action.path == "/":
        body = """
        <!doctype html><html><head><title>OWASP Juice Shop</title>
        <script src="runtime.js"></script><script src="main.js"></script>
        </head><body><app-root></app-root><a href="#/login">Login</a></body></html>
        """
        return WSTGLiveObservation(
            action_id=action.action_id,
            method="GET",
            url=url,
            status_code=200,
            reason="OK",
            headers={"Content-Type": "text/html", "Server": "test-server"},
            content_type="text/html",
            body_sha256="0" * 64,
            body_excerpt=body,
            body_size_bytes=len(body.encode()),
            elapsed_ms=1,
            wstg_ids=action.wstg_ids,
        )
    if "/api/" in action.path or action.path.startswith("/rest/"):
        return WSTGLiveObservation(
            action_id=action.action_id,
            method="GET",
            url=url,
            status_code=200,
            reason="OK",
            headers={"Content-Type": "application/json"},
            content_type="application/json",
            body_sha256="1" * 64,
            body_excerpt='[{"id": 1, "name": "Apple Juice"}]',
            body_size_bytes=34,
            elapsed_ms=1,
            wstg_ids=action.wstg_ids,
        )
    return WSTGLiveObservation(
        action_id=action.action_id,
        method="GET",
        url=url,
        status_code=404,
        reason="Not Found",
        headers={},
        content_type="text/plain",
        body_sha256="2" * 64,
        body_excerpt="not found",
        body_size_bytes=9,
        elapsed_ms=1,
        wstg_ids=action.wstg_ids,
        error="http_error",
    )


def test_generic_wstg_live_campaign_writes_state_evidence_and_proof_requests(tmp_path: Path) -> None:
    runtime = build_juice_shop_target_runtime(max_actions=5, max_ready_tests=15)
    result = run_wstg_live_campaign(
        WSTGLiveCampaignConfig(
            evidence_dir=tmp_path,
            target_runtime=runtime,
            campaign_id="local-juice-shop-generic",
            max_actions=5,
            proof_request_limit=8,
        ),
        action_executor=_observation,
    )

    assert result.target_alias == "local-juice-shop"
    assert result.request_count == 5
    assert "WSTG-v42-INFO-06" in result.observed_wstg_ids
    assert "WSTG-v42-APIT-01" in result.observed_wstg_ids
    assert result.benchmark_comparison is not None
    assert result.proof_requests
    assert any(finding.state == "needs_more_evidence" for finding in result.findings)
    assert any(decision.action == "request_missing_proof" for decision in result.decisions)

    expected_files = {
        "campaign/plan.json",
        "campaign/action-queue.json",
        "agent-decisions.jsonl",
        "state/final-campaign-state.json",
        "observations/http-observations.json",
        "surface/discovered-surface.json",
        "findings/candidate-findings.json",
        "proof-requests/proof-requests.json",
        "reports/campaign-report.md",
        "reports/benchmark-comparison.json",
        "campaign-result.json",
        "SHA256SUMS",
    }
    assert expected_files <= {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}


def test_generic_wstg_live_campaign_keeps_candidates_unvalidated(tmp_path: Path) -> None:
    runtime = build_juice_shop_target_runtime(max_actions=2, max_ready_tests=8)
    result = run_wstg_live_campaign(
        WSTGLiveCampaignConfig(evidence_dir=tmp_path, target_runtime=runtime, campaign_id="local-juice-shop-generic", max_actions=2),
        action_executor=_observation,
    )

    assert result.findings
    assert {finding.state for finding in result.findings} <= {"candidate", "observed", "needs_more_evidence"}
    assert "validated" not in {finding.state for finding in result.findings}
