from __future__ import annotations

import os
import subprocess
import sys
import tomllib


def test_v0_1_metadata_and_release_documents_are_present(project_root):
    metadata = tomllib.loads(
        (project_root / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert metadata["project"]["version"] == "0.1.0"
    for relative in (
        "LICENSE.md",
        "SECURITY.md",
        "docs/architecture-authority-review.md",
        "docs/dependency-license-inventory.md",
        "docs/repository-safety-review-v0.1.md",
        "examples/demo/dry-run-summary.example.json",
        "examples/demo/placeholder-report.example.md",
    ):
        assert (project_root / relative).is_file()


def test_v0_1_fast_release_check_passes(project_root):
    environment = os.environ.copy()
    environment["PYTHON"] = sys.executable
    completed = subprocess.run(
        [str(project_root / "scripts/check-v0.1-release.sh"), "--fast"],
        cwd=project_root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "v0.1 release check passed" in completed.stdout
    assert "validation_mode=fast" in completed.stdout
    assert "demo_summary=matched" in completed.stdout
    assert "placeholder_report=matched" in completed.stdout


def test_release_check_has_no_live_or_target_arguments(project_root):
    source = (project_root / "scripts/check-v0.1-release.sh").read_text(
        encoding="utf-8"
    )
    assert "--live" not in source
    assert "target_url" not in source
    assert "program-profile" not in source
