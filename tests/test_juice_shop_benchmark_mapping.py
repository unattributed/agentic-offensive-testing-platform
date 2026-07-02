import pytest

from aotp.benchmarks.juice_shop import build_juice_shop_benchmark_manifest, compare_wstg_observations
from aotp.wstg import WSTG_V42_CATALOG


def test_juice_shop_benchmark_maps_only_to_canonical_wstg_ids() -> None:
    catalog_ids = {case.wstg_id for case in WSTG_V42_CATALOG.cases()}
    manifest = build_juice_shop_benchmark_manifest()

    assert manifest.target_alias == "local-juice-shop"
    assert manifest.benchmark_version == "juice-shop-local-loopback-v1"
    assert len(manifest.categories) >= 8
    assert manifest.expected_wstg_ids
    assert manifest.expected_wstg_ids <= catalog_ids
    assert "WSTG-v42-INPV-01" in manifest.expected_wstg_ids
    assert "WSTG-v42-ATHZ-04" in manifest.expected_wstg_ids
    assert "WSTG-v42-APIT-01" in manifest.expected_wstg_ids


def test_juice_shop_benchmark_comparison_reports_detected_and_missed() -> None:
    comparison = compare_wstg_observations(
        [
            "WSTG-v42-INFO-02",
            "WSTG-v42-INPV-01",
            "WSTG-v42-ATHZ-04",
        ]
    )

    assert comparison["target_alias"] == "local-juice-shop"
    assert comparison["coverage"]["detected"] == 3
    assert comparison["coverage"]["missed"] > 0
    assert "WSTG-v42-INPV-01" in comparison["detected"]
    assert comparison["categories"]


def test_juice_shop_benchmark_comparison_rejects_unknown_wstg_ids() -> None:
    with pytest.raises(ValueError, match="unknown WSTG IDs"):
        compare_wstg_observations(["WSTG-v42-FAKE-99"])
