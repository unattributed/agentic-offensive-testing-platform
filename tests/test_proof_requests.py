from __future__ import annotations

from aotp.campaigns.proof_requests import build_proof_requests
from aotp.campaigns.target_runtime import build_juice_shop_target_runtime
from aotp.wstg import build_wstg_engine_plan


def test_proof_requests_track_missing_evidence_without_validating_findings() -> None:
    runtime = build_juice_shop_target_runtime(max_actions=3, max_ready_tests=12)
    plan = build_wstg_engine_plan(runtime.build_wstg_profile(campaign_id="local-juice-shop-generic", max_ready_tests=12))
    requests = build_proof_requests(plan, {"WSTG-v42-INFO-06"}, limit=5)

    assert requests
    assert len(requests) <= 5
    assert all(request.status == "needs_more_evidence" for request in requests)
    assert all(request.missing_evidence for request in requests)
    assert all(request.requested_agent for request in requests)
    assert "WSTG-v42-INFO-06" not in {request.wstg_id for request in requests}
