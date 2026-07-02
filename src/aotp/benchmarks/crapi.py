"""OWASP crAPI benchmark category mapping for AOTP campaigns.

The benchmark maps broad crAPI vulnerability classes to canonical WSTG IDs. It
intentionally avoids challenge solutions, credentials, or exploit payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from aotp.wstg import WSTG_V42_CATALOG


@dataclass(frozen=True)
class CapiBenchmarkCategory:
    """A broad crAPI vulnerability class mapped to canonical WSTG IDs."""

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
class CapiBenchmarkManifest:
    """Benchmark manifest used after an AOTP crAPI campaign completes."""

    target_alias: str
    benchmark_version: str
    categories: tuple[CapiBenchmarkCategory, ...]

    def __post_init__(self) -> None:
        if self.target_alias != "local-crapi":
            raise ValueError("crAPI benchmark target alias must be local-crapi")
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


def build_crapi_benchmark_manifest() -> CapiBenchmarkManifest:
    """Build the local crAPI benchmark mapping.

    These categories are broad WSTG-aligned expectations. They are intended for
    coverage comparison after AOTP observes evidence, not for memorizing crAPI.
    """

    return CapiBenchmarkManifest(
        target_alias="local-crapi",
        benchmark_version="crapi-local-loopback-v1",
        categories=(
            CapiBenchmarkCategory(
                benchmark_id="crapi-api-surface",
                name="API surface and architecture discovery",
                description="Application entry points, API routes, framework clues, and architecture mapping.",
                wstg_ids=(
                    "WSTG-v42-INFO-06",
                    "WSTG-v42-INFO-07",
                    "WSTG-v42-INFO-08",
                    "WSTG-v42-INFO-10",
                    "WSTG-v42-APIT-01",
                ),
            ),
            CapiBenchmarkCategory(
                benchmark_id="crapi-authentication",
                name="Authentication and identity workflows",
                description="Registration, login, password policy, reset, and alternate-channel authentication behavior.",
                wstg_ids=(
                    "WSTG-v42-ATHN-01",
                    "WSTG-v42-ATHN-02",
                    "WSTG-v42-ATHN-07",
                    "WSTG-v42-ATHN-09",
                    "WSTG-v42-ATHN-10",
                ),
            ),
            CapiBenchmarkCategory(
                benchmark_id="crapi-object-authorization",
                name="Object-level authorization and access control",
                description="BOLA, IDOR, privilege boundary, and authorization bypass behavior.",
                wstg_ids=(
                    "WSTG-v42-ATHZ-02",
                    "WSTG-v42-ATHZ-03",
                    "WSTG-v42-ATHZ-04",
                    "WSTG-v42-SESS-01",
                ),
            ),
            CapiBenchmarkCategory(
                benchmark_id="crapi-business-logic",
                name="Business logic and workflow integrity",
                description="Multi-step request forgery, workflow circumvention, reuse limits, and integrity checks.",
                wstg_ids=(
                    "WSTG-v42-BUSL-01",
                    "WSTG-v42-BUSL-02",
                    "WSTG-v42-BUSL-03",
                    "WSTG-v42-BUSL-05",
                    "WSTG-v42-BUSL-06",
                ),
            ),
            CapiBenchmarkCategory(
                benchmark_id="crapi-input-and-ssrf",
                name="Input handling and server-side request behavior",
                description="API input handling, injection-adjacent behavior, SSRF-style request paths, and error signals.",
                wstg_ids=(
                    "WSTG-v42-INPV-01",
                    "WSTG-v42-INPV-05",
                    "WSTG-v42-INPV-12",
                    "WSTG-v42-ERRH-01",
                    "WSTG-v42-CONF-06",
                ),
            ),
        ),
    )


def compare_crapi_wstg_observations(observed_wstg_ids: Iterable[str]) -> dict[str, Any]:
    """Compare observed WSTG IDs with the crAPI benchmark manifest."""

    manifest = build_crapi_benchmark_manifest()
    observed = frozenset(observed_wstg_ids)
    expected = manifest.expected_wstg_ids
    detected = observed & expected
    missed = expected - observed
    extra = observed - expected
    category_results = []
    for category in manifest.categories:
        category_expected = frozenset(category.wstg_ids)
        category_detected = observed & category_expected
        category_results.append(
            {
                "benchmark_id": category.benchmark_id,
                "name": category.name,
                "expected_wstg_ids": sorted(category_expected),
                "detected_wstg_ids": sorted(category_detected),
                "missed_wstg_ids": sorted(category_expected - category_detected),
                "coverage_ratio": len(category_detected) / len(category_expected),
            }
        )
    return {
        "target_alias": manifest.target_alias,
        "benchmark_version": manifest.benchmark_version,
        "expected_wstg_id_count": len(expected),
        "observed_wstg_id_count": len(observed),
        "detected_expected_count": len(detected),
        "missed_expected_count": len(missed),
        "extra_observed_count": len(extra),
        "detected_wstg_ids": sorted(detected),
        "missed_wstg_ids": sorted(missed),
        "extra_observed_wstg_ids": sorted(extra),
        "category_results": category_results,
    }
