from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _copy_scripts(project_root: Path, tmp_path: Path) -> Path:
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    for name in ("validate-vault-leakage.sh", "validate-repository-safety.sh"):
        script = script_dir / name
        shutil.copy2(project_root / "scripts" / name, script)
        script.chmod(script.stat().st_mode | 0o100)
    return script_dir


def test_vault_leakage_script_passes_safe_repository(project_root: Path, tmp_path: Path):
    scripts = _copy_scripts(project_root, tmp_path)
    (tmp_path / "README.md").write_text("vault handles only\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["GIT_CEILING_DIRECTORIES"] = str(tmp_path)
    completed = subprocess.run(
        [str(scripts / "validate-vault-leakage.sh")],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "vault leakage validation passed" in completed.stdout


def test_vault_leakage_script_blocks_plaintext_marker(project_root: Path, tmp_path: Path):
    scripts = _copy_scripts(project_root, tmp_path)
    (tmp_path / "unsafe.txt").write_text("vault" + "_plaintext: synthetic", encoding="utf-8")
    environment = os.environ.copy()
    environment["GIT_CEILING_DIRECTORIES"] = str(tmp_path)
    completed = subprocess.run(
        [str(scripts / "validate-vault-leakage.sh")],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "plaintext vault marker" in completed.stdout


def test_repository_safety_calls_vault_leakage_script(project_root: Path, tmp_path: Path):
    scripts = _copy_scripts(project_root, tmp_path)
    (tmp_path / "unsafe.txt").write_text("raw" + "_vault_material = synthetic", encoding="utf-8")
    environment = os.environ.copy()
    environment["GIT_CEILING_DIRECTORIES"] = str(tmp_path)
    completed = subprocess.run(
        [str(scripts / "validate-repository-safety.sh")],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "vault leakage validation failed" in completed.stdout
