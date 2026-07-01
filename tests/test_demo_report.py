from __future__ import annotations

import subprocess
import sys

from aotp.demo_release import generate_placeholder_report


def test_placeholder_report_matches_tracked_example(project_root):
    report = generate_placeholder_report()
    expected = (
        project_root / "examples/demo/placeholder-report.example.md"
    ).read_text(encoding="utf-8")
    assert report == expected
    assert "does not infer vulnerabilities" in report
    assert "Report-ready findings: `0`" in report
    assert "No evidence-bound candidate" in report
    assert "Target alias: `local-placeholder`" in report
    assert "Request count" not in report


def test_placeholder_report_script_is_reproducible(project_root, tmp_path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    for output in (first, second):
        completed = subprocess.run(
            [
                sys.executable,
                str(project_root / "scripts/generate-placeholder-report.py"),
                "--output",
                str(output),
            ],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
    assert first.read_bytes() == second.read_bytes()
