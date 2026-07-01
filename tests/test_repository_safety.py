from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def test_non_git_repository_scan_ignores_generated_local_paths(
    project_root: Path,
    tmp_path: Path,
):
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    script = script_dir / "validate-repository-safety.sh"
    shutil.copy2(project_root / "scripts/validate-repository-safety.sh", script)
    script.chmod(script.stat().st_mode | 0o100)
    (tmp_path / "README.md").write_text("safe extracted archive\n", encoding="utf-8")

    generated_files = [
        tmp_path / ".pytest_cache/v/cache/nodeids",
        tmp_path / "__pycache__/module.pyc",
        tmp_path / ".venv/cache.txt",
        tmp_path / "build/cache.txt",
        tmp_path / "dist/cache.txt",
        tmp_path / "package.egg-info/cache.txt",
        tmp_path / ".aotp/evidence/cache.txt",
    ]
    marker = "Cookie: session=generated-local-value"
    for path in generated_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(marker, encoding="utf-8")

    environment = os.environ.copy()
    environment["GIT_CEILING_DIRECTORIES"] = str(tmp_path)
    completed = subprocess.run(
        [str(script)],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "repository safety validation passed" in completed.stdout


def test_non_git_repository_scan_detects_case_insensitive_secret_marker(
    project_root: Path,
    tmp_path: Path,
):
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    script = script_dir / "validate-repository-safety.sh"
    shutil.copy2(project_root / "scripts/validate-repository-safety.sh", script)
    script.chmod(script.stat().st_mode | 0o100)
    marker = "Cookie" + ": session=tracked-secret-value"
    (tmp_path / "unsafe.txt").write_text(marker, encoding="utf-8")

    environment = os.environ.copy()
    environment["GIT_CEILING_DIRECTORIES"] = str(tmp_path)
    completed = subprocess.run(
        [str(script)],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "likely secret or private evidence" in completed.stdout
