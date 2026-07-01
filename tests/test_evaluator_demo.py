from __future__ import annotations

import json
import os
import subprocess
import sys


def test_evaluator_demo_completes_without_requests(project_root, tmp_path):
    workspace = tmp_path / "demo"
    environment = os.environ.copy()
    environment["AOTP_DEMO_PYTHON"] = sys.executable
    completed = subprocess.run(
        [str(project_root / "scripts/run-evaluator-demo.sh"), str(workspace)],
        cwd=project_root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    summary = json.loads(
        (workspace / ".aotp/demo/summary.json").read_text(encoding="utf-8")
    )
    assert summary == {
        "campaign_id": "example-webapp-dry-run",
        "completed_objectives": [
            "wstg-security-headers",
            "wstg-authn-session",
        ],
        "demonstration_data": "placeholder_only",
        "evidence_records": 2,
        "network_mode": "network_silent",
        "report_limitations_declared": True,
        "report_ready_findings": 0,
        "request_count": 0,
        "schema_version": "1.0",
        "status": "completed",
    }
    assert json.loads(
        (workspace / ".aotp/demo/events-verify.json").read_text(encoding="utf-8")
    )["valid"] is True
    report = (workspace / ".aotp/demo/placeholder-report.md").read_text(
        encoding="utf-8"
    )
    assert "No evidence-bound candidate" in report
    assert "Report-ready findings: `0`" in report


def test_evaluator_demo_rejects_workspace_with_existing_state(project_root, tmp_path):
    workspace = tmp_path / "demo"
    (workspace / ".aotp").mkdir(parents=True)
    environment = os.environ.copy()
    environment["AOTP_DEMO_PYTHON"] = sys.executable
    completed = subprocess.run(
        [str(project_root / "scripts/run-evaluator-demo.sh"), str(workspace)],
        cwd=project_root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "already contains .aotp state" in completed.stderr
