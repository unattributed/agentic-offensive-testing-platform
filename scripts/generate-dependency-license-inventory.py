#!/usr/bin/env python3
"""Generate a conservative installed-distribution license inventory."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from importlib.metadata import PackageNotFoundError, distribution, distributions
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"
REVIEW_STATUSES = {
    "owner_controlled_proprietary",
    "metadata_recorded_pending_legal_review",
    "notice_and_file_scope_review",
    "distribution_blocked_pending_legal_review",
    "manual_metadata_review_required",
}


def _roots(root: Path) -> dict[str, str]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    result = {
        canonicalize_name(project["name"]): "project",
    }
    groups = (
        ("dependencies", "direct_runtime", project.get("dependencies", [])),
        (
            "optional-dependencies.dev",
            "direct_development",
            project.get("optional-dependencies", {}).get("dev", []),
        ),
        (
            "optional-dependencies.audit",
            "direct_audit_tool",
            project.get("optional-dependencies", {}).get("audit", []),
        ),
    )
    for _, category, requirements in groups:
        for value in requirements:
            result[canonicalize_name(Requirement(value).name)] = category
    return result


def _license(metadata: Any) -> str:
    expression = metadata.get("License-Expression")
    if expression and expression.strip():
        return expression.strip()
    legacy = metadata.get("License")
    if legacy and legacy.strip() and legacy.strip().upper() != "UNKNOWN":
        return legacy.strip()
    classifiers = [
        value.split(" :: ")[-1]
        for value in metadata.get_all("Classifier", [])
        if value.startswith("License ::")
    ]
    return " OR ".join(classifiers) if classifiers else "UNKNOWN"


def _source(metadata: Any) -> str:
    for value in metadata.get_all("Project-URL", []):
        label, separator, url = value.partition(",")
        if separator and label.strip().lower() in {
            "homepage",
            "repository",
            "source",
            "source code",
        }:
            return url.strip()
    return (metadata.get("Home-page") or "UNKNOWN").strip()


def _review_status(name: str, license_expression: str) -> str:
    if name == "agentic-offensive-testing-platform":
        return "owner_controlled_proprietary"
    upper = license_expression.upper()
    if license_expression == "UNKNOWN":
        return "manual_metadata_review_required"
    if "AGPL" in upper or "LGPL" in upper or "GPL" in upper:
        return "distribution_blocked_pending_legal_review"
    if "MPL" in upper:
        return "notice_and_file_scope_review"
    return "metadata_recorded_pending_legal_review"


def generate(root: Path = ROOT) -> dict[str, Any]:
    roots = _roots(root)
    records: dict[str, dict[str, str]] = {}
    for installed in distributions():
        metadata = installed.metadata
        raw_name = metadata.get("Name")
        if not raw_name:
            continue
        name = canonicalize_name(raw_name)
        license_expression = _license(metadata)
        record = {
            "name": name,
            "version": installed.version,
            "dependency_type": roots.get(name, "transitive"),
            "license_metadata": license_expression,
            "source": _source(metadata),
            "review_status": _review_status(name, license_expression),
        }
        existing = records.get(name)
        if existing is None or existing["version"] < record["version"]:
            records[name] = record
    missing = []
    for name in roots:
        if name not in records:
            try:
                distribution(name)
            except PackageNotFoundError:
                missing.append(name)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "scripts/generate-dependency-license-inventory.py",
        "python_version": ".".join(str(value) for value in sys.version_info[:3]),
        "missing_declared_distributions": sorted(missing),
        "review_statuses": sorted(REVIEW_STATUSES),
        "dependencies": sorted(records.values(), key=lambda item: item["name"]),
    }


def validate_inventory(inventory: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if inventory.get("schema_version") != SCHEMA_VERSION:
        failures.append("unsupported inventory schema")
    if inventory.get("missing_declared_distributions"):
        failures.append("declared distributions are missing")
    dependencies = inventory.get("dependencies")
    if not isinstance(dependencies, list) or not dependencies:
        failures.append("dependency inventory is empty")
        return failures
    names: set[str] = set()
    categories: set[str] = set()
    for record in dependencies:
        name = record.get("name")
        if not name or name in names:
            failures.append("dependency names are missing or duplicated")
        names.add(name)
        categories.add(record.get("dependency_type"))
        if record.get("review_status") not in REVIEW_STATUSES:
            failures.append(f"dependency has no review status: {name}")
        if not record.get("license_metadata"):
            failures.append(f"dependency has no license metadata result: {name}")
    required_categories = {
        "project",
        "direct_runtime",
        "direct_development",
        "direct_audit_tool",
        "transitive",
    }
    if missing_categories := sorted(required_categories - categories):
        failures.append(
            "dependency categories are missing: " + ", ".join(missing_categories)
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs/dependency-license-inventory.json"),
    )
    arguments = parser.parse_args()
    inventory = generate()
    failures = validate_inventory(inventory)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    output = Path(arguments.output)
    output.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"dependency license inventory written: {output}")
    print(f"dependency_count={len(inventory['dependencies'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
