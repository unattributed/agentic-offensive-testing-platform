#!/usr/bin/env python3
"""Verify that source and package metadata preserve the proprietary posture."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = metadata.get("project", {})
    if project.get("license") != "LicenseRef-Proprietary":
        failures.append("project license expression is not LicenseRef-Proprietary")
    if project.get("license-files") != ["LICENSE.md"]:
        failures.append("project license files do not name LICENSE.md exactly")
    classifiers = project.get("classifiers", [])
    if any(str(value).startswith("License :: OSI Approved") for value in classifiers):
        failures.append("project metadata contains an open-source license classifier")
    build_requirements = metadata.get("build-system", {}).get("requires", [])
    if "setuptools>=77.0.3" not in build_requirements:
        failures.append("build backend does not require PEP 639 capable setuptools")

    license_text = (root / "LICENSE.md").read_text(encoding="utf-8")
    required = (
        "All rights reserved.",
        "No open-source license is granted.",
        "No permission is granted to copy, modify, distribute, sublicense, operate, or use",
    )
    for statement in required:
        if statement not in license_text:
            failures.append(f"license is missing required statement: {statement}")
    return failures


def main() -> int:
    failures = audit()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("proprietary license audit passed")
    print("license_expression=LicenseRef-Proprietary")
    print("license_file=LICENSE.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
