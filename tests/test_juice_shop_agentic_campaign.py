from __future__ import annotations

from pathlib import Path

import pytest

from aotp.campaigns.juice_shop_campaign import (
    AgenticCampaignObservation,
    JuiceShopCampaignError,
    LocalJuiceShopCampaignConfig,
    run_local_juice_shop_agentic_campaign,
)


def _observation(method: str, url: str, status: int, body: str, content_type: str = "text/html") -> AgenticCampaignObservation:
    return AgenticCampaignObservation(
        method=method,
        url=url,
        status_code=status,
        reason="OK" if status < 400 else "Not Found",
        headers={"Content-Type": content_type, "Server": "test-server"},
        content_type=content_type,
        body_sha256="0" * 64,
        body_excerpt=body,
        body_size_bytes=len(body.encode()),
        elapsed_ms=1,
        error=None if status < 400 else "http_error",
    )


def _fake_http_client(method: str, url: str, timeout: float) -> AgenticCampaignObservation:
    assert method == "GET"
    assert timeout > 0
    if url.endswith("/"):
        return _observation(
            method,
            url,
            200,
            """
            <!doctype html>
            <html><head><title>OWASP Juice Shop</title>
            <script src="runtime.js"></script><script src="main.js"></script>
            </head><body><app-root></app-root><a href="#/login">Login</a></body></html>
            """,
        )
    if url.endswith("/api/Products") or url.endswith("/rest/products/search?q="):
        return _observation(method, url, 200, '[{"id": 1, "name": "Apple Juice"}]', "application/json")
    return _observation(method, url, 404, "not found")


def test_local_juice_shop_agentic_campaign_writes_evidence(tmp_path: Path) -> None:
    config = LocalJuiceShopCampaignConfig(evidence_dir=tmp_path, max_requests=5, max_ready_tests=12)
    result = run_local_juice_shop_agentic_campaign(config, http_client=_fake_http_client)

    assert result.target_alias == "local-juice-shop"
    assert result.base_url == "http://127.0.0.1:3000/"
    assert result.request_count == 5
    assert "WSTG-v42-INFO-06" in result.observed_wstg_ids
    assert "WSTG-v42-APIT-01" in result.observed_wstg_ids
    assert "WSTG-v42-CLNT-01" in result.observed_wstg_ids
    assert result.benchmark_comparison["coverage"]["detected"] > 0
    assert result.benchmark_comparison["coverage"]["missed"] > 0
    assert any(finding.finding_id == "js-observed-api-surface" for finding in result.findings)
    assert any(finding.status == "manual_required" for finding in result.findings)

    expected_files = {
        "campaign-plan.json",
        "agent-decisions.jsonl",
        "campaign-result.json",
        "observations/http-observations.json",
        "surface/discovered-surface.json",
        "findings/candidate-findings.json",
        "reports/benchmark-comparison.json",
        "reports/campaign-report.md",
        "SHA256SUMS",
    }
    assert expected_files <= {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}


def test_local_juice_shop_agentic_campaign_is_state_driven(tmp_path: Path) -> None:
    config = LocalJuiceShopCampaignConfig(evidence_dir=tmp_path, max_requests=3, max_ready_tests=8)
    result = run_local_juice_shop_agentic_campaign(config, http_client=_fake_http_client)

    actions = [decision.action for decision in result.decisions]
    assert actions[0] == "build_wstg_campaign_plan"
    assert "http_get_safe_path" in actions
    assert "derive_surface_inventory" in actions
    assert "create_candidate_findings" in actions
    assert actions[-1] == "compare_benchmark_coverage"
    assert all(decision.status in {"completed", "observed_error"} for decision in result.decisions)


def test_local_juice_shop_agentic_campaign_rejects_non_loopback_targets(tmp_path: Path) -> None:
    with pytest.raises(JuiceShopCampaignError):
        LocalJuiceShopCampaignConfig(evidence_dir=tmp_path, base_url="http://example.com:3000/")


@pytest.mark.parametrize("safe_path", ["http://127.0.0.1:3000/", "//127.0.0.1:3000/", "relative", "/../etc/passwd"])
def test_local_juice_shop_agentic_campaign_rejects_unsafe_safe_paths(tmp_path: Path, safe_path: str) -> None:
    with pytest.raises(JuiceShopCampaignError):
        LocalJuiceShopCampaignConfig(evidence_dir=tmp_path, safe_paths=(safe_path,))
