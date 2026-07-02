"""Benchmark manifests for controlled AOTP validation targets."""

from .juice_shop import (
    JuiceShopBenchmarkCategory,
    JuiceShopBenchmarkManifest,
    build_juice_shop_benchmark_manifest,
    compare_wstg_observations,
)

__all__ = [
    "JuiceShopBenchmarkCategory",
    "JuiceShopBenchmarkManifest",
    "build_juice_shop_benchmark_manifest",
    "compare_wstg_observations",
]
