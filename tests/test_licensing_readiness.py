from __future__ import annotations

import importlib.util
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
