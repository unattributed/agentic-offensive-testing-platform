"""Benchmark manifests for controlled AOTP validation targets."""

from .crapi import (
    CapiBenchmarkCategory,
    CapiBenchmarkManifest,
    build_crapi_benchmark_manifest,
    compare_crapi_wstg_observations,
)
from .juice_shop import (
    JuiceShopBenchmarkCategory,
    JuiceShopBenchmarkManifest,
    build_juice_shop_benchmark_manifest,
    compare_wstg_observations,
)

__all__ = [
    "CapiBenchmarkCategory",
    "CapiBenchmarkManifest",
    "JuiceShopBenchmarkCategory",
    "JuiceShopBenchmarkManifest",
    "build_crapi_benchmark_manifest",
    "build_juice_shop_benchmark_manifest",
    "compare_crapi_wstg_observations",
    "compare_wstg_observations",
]
