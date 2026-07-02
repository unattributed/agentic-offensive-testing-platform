"""OWASP Juice Shop benchmark category mapping for AOTP campaigns.

This benchmark compares AOTP-observed WSTG coverage against broad expected
vulnerability classes. It intentionally avoids challenge solutions and payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from aotp.wstg import WSTG_V42_CATALOG


@dataclass(frozen=True)
class JuiceShopBenchmarkCategory:
    """A broad Juice Shop vulnerability class mapped to canonical WSTG IDs."""

    benchmark_id: str
    name: str
    description: str
    wstg_ids: tuple[str, ...]
    expected_disposition: str = "detect_or_explain"

    def as_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "description": self.description,
            "wstg_ids": list(self.wstg_ids),
            "expected_disposition": self.expected_disposition,
        }


@dataclass(frozen=True)
class JuiceShopBenchmarkManifest:
    """Benchmark manifest used after an AOTP campaign completes."""

    target_alias: str
    benchmark_version: str
    categories: tuple[JuiceShopBenchmarkCategory, ...]

    def __post_init__(self) -> None:
        if self.target_alias != "local-juice-shop":
            raise ValueError("Juice Shop benchmark target alias must be local-juice-shop")
        if not self.categories:
            raise ValueError("benchmark categories are required")
        seen: set[str] = set()
        catalog_ids = {case.wstg_id for case in WSTG_V42_CATALOG.cases()}
        for category in self.categories:
            if category.benchmark_id in seen:
                raise ValueError(f"duplicate benchmark category: {category.benchmark_id}")
            seen.add(category.benchmark_id)
            missing = set(category.wstg_ids) - catalog_ids
            if missing:
                raise ValueError(f"benchmark category maps unknown WSTG IDs: {sorted(missing)!r}")

    @property
    def expected_wstg_ids(self) -> frozenset[str]:
        ids: set[str] = set()
        for category in self.categories:
            ids.update(category.wstg_ids)
        return frozenset(ids)

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_alias": self.target_alias,
            "benchmark_version": self.benchmark_version,
            "expected_wstg_ids": sorted(self.expected_wstg_ids),
            "categories": [category.as_dict() for category in self.categories],
        }


def build_juice_shop_benchmark_manifest() -> JuiceShopBenchmarkManifest:
    """Build the local Juice Shop benchmark mapping.

    These categories are intentionally broad. The benchmark asks whether AOTP
    exercised and reported the related WSTG classes, not whether it memorized
    Juice Shop challenge solutions.
    """

    return JuiceShopBenchmarkManifest(
        target_alias="local-juice-shop",
        benchmark_version="juice-shop-local-loopback-v1",
        categories=(
            JuiceShopBenchmarkCategory(
                benchmark_id="js-info-surface",
                name="Application surface and metadata",
                description="Routes, entry points, framework clues, and API surface discovery.",
                wstg_ids=(
                    "WSTG-v42-INFO-02",
                    "WSTG-v42-INFO-05",
                    "WSTG-v42-INFO-06",
                    "WSTG-v42-INFO-08",
                    "WSTG-v42-APIT-01",
                ),
            ),
            JuiceShopBenchmarkCategory(
                benchmark_id="js-authentication",
                name="Authentication and account workflows",
                description="Login, registration, password reset, credential policy, and MFA-adjacent behavior.",
                wstg_ids=(
                    "WSTG-v42-ATHN-01",
                    "WSTG-v42-ATHN-02",
                    "WSTG-v42-ATHN-03",
                    "WSTG-v42-ATHN-07",
                    "WSTG-v42-ATHN-09",
                ),
            ),
            JuiceShopBenchmarkCategory(
                benchmark_id="js-authorization",
                name="Authorization and access control",
                description="Horizontal, vertical, and direct object access control behavior.",
                wstg_ids=(
                    "WSTG-v42-ATHZ-01",
                    "WSTG-v42-ATHZ-02",
                    "WSTG-v42-ATHZ-03",
                    "WSTG-v42-ATHZ-04",
                ),
            ),
            JuiceShopBenchmarkCategory(
                benchmark_id="js-session",
                name="Session and cookie handling",
                description="Session attributes, logout behavior, session fixation signals, and cookie scope.",
                wstg_ids=(
                    "WSTG-v42-SESS-02",
                    "WSTG-v42-SESS-03",
                    "WSTG-v42-SESS-06",
                    "WSTG-v42-SESS-07",
                ),
            ),
            JuiceShopBenchmarkCategory(
                benchmark_id="js-input-validation",
                name="Input validation vulnerability classes",
                description="XSS, injection, file handling, SSRF-style, and deserialization-adjacent classes.",
                wstg_ids=(
                    "WSTG-v42-INPV-01",
                    "WSTG-v42-INPV-05",
                    "WSTG-v42-INPV-11",
                    "WSTG-v42-INPV-12",
                    "WSTG-v42-INPV-13",
                    "WSTG-v42-INPV-19",
                ),
            ),
            JuiceShopBenchmarkCategory(
                benchmark_id="js-client-side",
                name="Client-side behavior",
                description="DOM behavior, client-side storage, CORS, cross-site messaging, and frontend controls.",
                wstg_ids=(
                    "WSTG-v42-CLNT-01",
                    "WSTG-v42-CLNT-04",
                    "WSTG-v42-CLNT-07",
                    "WSTG-v42-CLNT-10",
                    "WSTG-v42-CLNT-11",
                    "WSTG-v42-CLNT-13",
                ),
            ),
            JuiceShopBenchmarkCategory(
                benchmark_id="js-business-logic",
                name="Business logic and workflow abuse",
                description="Workflow bypass, unexpected use, integrity, and anti-automation behavior.",
                wstg_ids=(
                    "WSTG-v42-BUSL-01",
                    "WSTG-v42-BUSL-04",
                    "WSTG-v42-BUSL-05",
                    "WSTG-v42-BUSL-08",
                    "WSTG-v42-BUSL-09",
                ),
            ),
            JuiceShopBenchmarkCategory(
                benchmark_id="js-crypto-error-config",
                name="Configuration, cryptography, and error handling",
                description="Security headers, TLS-adjacent observations, weak crypto signals, and error leakage.",
                wstg_ids=(
                    "WSTG-v42-CONF-01",
                    "WSTG-v42-CONF-07",
                    "WSTG-v42-ERRH-01",
                    "WSTG-v42-CRYP-01",
                    "WSTG-v42-CRYP-04",
                ),
            ),
        ),
    )


def compare_wstg_observations(observed_wstg_ids: Iterable[str]) -> dict[str, Any]:
    """Compare observed WSTG IDs to the Juice Shop benchmark manifest."""

    manifest = build_juice_shop_benchmark_manifest()
    observed = set(observed_wstg_ids)
    unknown = observed - {case.wstg_id for case in WSTG_V42_CATALOG.cases()}
    if unknown:
        raise ValueError(f"observed unknown WSTG IDs: {sorted(unknown)!r}")
    detected = sorted(manifest.expected_wstg_ids & observed)
    missed = sorted(manifest.expected_wstg_ids - observed)
    extra = sorted(observed - manifest.expected_wstg_ids)
    by_category = []
    for category in manifest.categories:
        expected = set(category.wstg_ids)
        by_category.append(
            {
                "benchmark_id": category.benchmark_id,
                "name": category.name,
                "detected": sorted(expected & observed),
                "missed": sorted(expected - observed),
                "status": "covered" if expected <= observed else "partial_or_missing",
            }
        )
    return {
        "target_alias": manifest.target_alias,
        "benchmark_version": manifest.benchmark_version,
        "detected": detected,
        "missed": missed,
        "extra_observed": extra,
        "coverage": {
            "expected": len(manifest.expected_wstg_ids),
            "detected": len(detected),
            "missed": len(missed),
        },
        "categories": by_category,
    }
