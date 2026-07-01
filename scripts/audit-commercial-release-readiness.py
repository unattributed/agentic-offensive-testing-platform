#!/usr/bin/env python3
"""Fail closed unless commercial and licensing release blockers remain explicit."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_BLOCKER_AREAS = {
    "legal_terms",
    "dependency_obligations",
    "provenance",
    "evaluator_terms",
    "commercialization",
    "release_artifacts",
}


def audit(root: Path = ROOT, *, run_repository_commands: bool = True) -> list[str]:
    failures: list[str] = []
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    if metadata["project"].get("license") != "LicenseRef-Proprietary":
        failures.append("project license posture is not proprietary")

    review = yaml.safe_load(
        (root / "docs/public-release-risk-review.yaml").read_text(encoding="utf-8")
    )
    if review.get("schema_version") != "1.0":
        failures.append("public release review schema is unsupported")
    if review.get("repository_visibility", {}).get("observed") != "public":
        failures.append("recorded repository visibility is not current public posture")
    decisions = review.get("decisions", {})
    required_decisions = {
        "commercial_distribution": "blocked",
        "open_source_license_release": "blocked",
        "evaluator_distribution": "blocked",
        "operational_material_release": "prohibited",
    }
    for name, expected in required_decisions.items():
        if decisions.get(name) != expected:
            failures.append(f"release decision is not fail-closed: {name}")
    blockers = review.get("blockers", [])
    blocker_areas = {item.get("area") for item in blockers}
    if missing := sorted(REQUIRED_BLOCKER_AREAS - blocker_areas):
        failures.append("public release blocker areas are missing: " + ", ".join(missing))
    for item in blockers:
        if (
            item.get("status") != "blocked"
            or not item.get("evidence")
            or not item.get("required_action")
        ):
            failures.append(f"public release blocker is incomplete: {item.get('id')}")

    commercialization = yaml.safe_load(
        (root / "docs/commercialization-readiness.yaml").read_text(
            encoding="utf-8"
        )
    )
    if commercialization.get("decision") != "blocked":
        failures.append("commercialization decision is not blocked")
    if not any(
        item.get("status") in {"open", "blocked"}
        for item in commercialization.get("items", [])
    ):
        failures.append("commercialization has no visible open items")

    inventory = root / "docs/dependency-license-inventory.json"
    if not inventory.is_file():
        failures.append("dependency license inventory is missing")

    if run_repository_commands:
        for command in (
            [str(root / "scripts/validate-repository-safety.sh")],
            [str(root / "scripts/audit-repository-release.sh")],
        ):
            completed = subprocess.run(
                command,
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode:
                failures.append(
                    f"repository audit failed: {Path(command[0]).name}"
                )
    return failures


def main() -> int:
    failures = audit()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("commercial release readiness audit passed")
    print("repository_visibility=public")
    print("source_license=proprietary_all_rights_reserved")
    print("commercial_distribution=blocked")
    print("open_source_license_release=blocked")
    print("evaluator_distribution=blocked")
    print("operational_material_release=prohibited")
    return 0


if __name__ == "__main__":
    sys.exit(main())
