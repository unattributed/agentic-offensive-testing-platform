from aotp.benchmarks.crapi import build_crapi_benchmark_manifest, compare_crapi_wstg_observations
from aotp.wstg import WSTG_V42_CATALOG


def test_crapi_benchmark_manifest_maps_only_canonical_wstg_ids() -> None:
    manifest = build_crapi_benchmark_manifest()
    catalog_ids = {case.wstg_id for case in WSTG_V42_CATALOG.cases()}

    assert manifest.target_alias == "local-crapi"
    assert manifest.benchmark_version == "crapi-local-loopback-v1"
    assert len(manifest.categories) >= 5
    assert "WSTG-v42-ATHZ-04" in manifest.expected_wstg_ids
    assert "WSTG-v42-BUSL-06" in manifest.expected_wstg_ids
    assert "WSTG-v42-APIT-01" in manifest.expected_wstg_ids
    assert manifest.expected_wstg_ids <= catalog_ids


def test_crapi_benchmark_comparison_reports_detected_missed_and_extra_ids() -> None:
    comparison = compare_crapi_wstg_observations(
        [
            "WSTG-v42-INFO-06",
            "WSTG-v42-ATHZ-04",
            "WSTG-v42-BUSL-06",
            "WSTG-v42-CLNT-01",
        ]
    )

    assert comparison["target_alias"] == "local-crapi"
    assert comparison["detected_expected_count"] == 3
    assert "WSTG-v42-ATHZ-04" in comparison["detected_wstg_ids"]
    assert "WSTG-v42-CLNT-01" in comparison["extra_observed_wstg_ids"]
    assert comparison["missed_expected_count"] > 0
    assert any(row["benchmark_id"] == "crapi-object-authorization" for row in comparison["category_results"])
