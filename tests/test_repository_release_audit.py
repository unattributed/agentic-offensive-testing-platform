from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _run(*args, cwd: Path):
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _repository(project_root: Path, tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in ("audit-repository-release.sh", "validate-repository-safety.sh"):
        destination = scripts / name
        shutil.copy2(project_root / "scripts" / name, destination)
        destination.chmod(destination.stat().st_mode | 0o100)
    assert _run("git", "init", "-q", cwd=root).returncode == 0
    assert _run("git", "config", "user.name", "test", cwd=root).returncode == 0
    assert _run(
        "git", "config", "user.email", "test@example.invalid", cwd=root
    ).returncode == 0
    assert _run("git", "config", "commit.gpgsign", "false", cwd=root).returncode == 0
    (root / "README.md").write_text("safe placeholder repository\n", encoding="utf-8")
    assert _run("git", "add", ".", cwd=root).returncode == 0
    assert _run("git", "commit", "-qm", "safe baseline", cwd=root).returncode == 0
    return root


def test_repository_release_audit_accepts_safe_history(project_root, tmp_path):
    root = _repository(project_root, tmp_path)
    completed = _run("./scripts/audit-repository-release.sh", cwd=root)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "repository release audit passed" in completed.stdout
    assert "history_secret_findings=0" in completed.stdout


def test_repository_release_audit_detects_secret_in_deleted_history(
    project_root,
    tmp_path,
):
    root = _repository(project_root, tmp_path)
    secret = "Cookie" + ": session=historical-secret"
    leak = root / "temporary.txt"
    leak.write_text(secret + "\n", encoding="utf-8")
    assert _run("git", "add", "temporary.txt", cwd=root).returncode == 0
    assert _run("git", "commit", "-qm", "temporary file", cwd=root).returncode == 0
    leak.unlink()
    assert _run("git", "add", "temporary.txt", cwd=root).returncode == 0
    assert _run("git", "commit", "-qm", "remove temporary file", cwd=root).returncode == 0

    completed = _run("./scripts/audit-repository-release.sh", cwd=root)
    assert completed.returncode == 1
    assert "likely secret found in commit" in completed.stdout
    assert "historical-secret" in completed.stdout


def test_repository_release_audit_requires_git_worktree(project_root, tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("audit-repository-release.sh", "validate-repository-safety.sh"):
        destination = scripts / name
        shutil.copy2(project_root / "scripts" / name, destination)
        destination.chmod(destination.stat().st_mode | 0o100)
    environment = os.environ.copy()
    environment["GIT_CEILING_DIRECTORIES"] = str(tmp_path)
    completed = subprocess.run(
        [str(scripts / "audit-repository-release.sh")],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "Git worktree required" in completed.stderr
