from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path


def _load_script(project_root: Path, name: str):
    path = project_root / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_proprietary_license_audit_passes(project_root):
    module = _load_script(project_root, "audit-proprietary-license.py")
    assert module.audit(project_root) == []


def test_built_wheel_declares_proprietary_license(project_root, tmp_path):
    completed = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    wheel = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = archive.read(metadata_name).decode()
        assert "License-Expression: LicenseRef-Proprietary" in metadata
        assert "License-File: LICENSE.md" in metadata
        assert any(name.endswith(".dist-info/licenses/LICENSE.md") for name in archive.namelist())


def test_dependency_inventory_covers_declared_and_transitive_packages(project_root):
    module = _load_script(
        project_root, "generate-dependency-license-inventory.py"
    )
    inventory = module.generate(project_root)
    assert module.validate_inventory(inventory) == []
    categories = {
        record["dependency_type"] for record in inventory["dependencies"]
    }
    assert {
        "project",
        "direct_runtime",
        "direct_development",
        "direct_audit_tool",
        "transitive",
    }.issubset(categories)
    assert all(record["review_status"] for record in inventory["dependencies"])


def test_tracked_dependency_inventory_is_valid(project_root):
    module = _load_script(
        project_root, "generate-dependency-license-inventory.py"
    )
    inventory = json.loads(
        (project_root / "docs/dependency-license-inventory.json").read_text(
            encoding="utf-8"
        )
    )
    assert module.validate_inventory(inventory) == []


def test_provenance_policy_blocks_unclear_material(project_root):
    policy = (
        project_root / "docs/third-party-attribution-policy.md"
    ).read_text(encoding="utf-8")
    contributing = (project_root / "CONTRIBUTING.md").read_text(encoding="utf-8")
    template = (
        project_root / ".github/pull_request_template.md"
    ).read_text(encoding="utf-8")
    register = (
        project_root / "docs/third-party-provenance-register.md"
    ).read_text(encoding="utf-8")

    for required in (
        "immutable version",
        "exact license expression",
        "clean-room",
        "legal_review_required",
        "missing or incomplete",
    ):
        assert required in policy
    assert "Only a provenance decision of `accepted` permits merge" in contributing
    assert "any other status blocks merge" in template
    assert "No source or prose copied" in register
