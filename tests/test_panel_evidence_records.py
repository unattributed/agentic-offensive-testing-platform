from __future__ import annotations

import json
from pathlib import Path

from aotp.cli import main
from aotp.config import load_yaml
from aotp.control_panel import PANEL_SAFE_OBSERVATIONS
from aotp.evidence import EvidenceManifest, load_manifest, register_artifact, verify_evidence_directory, write_manifest
from aotp.executor import execute
from aotp.panel_evidence import (
    PANEL_EVIDENCE_FILE,
    build_panel_evidence_record,
    validate_panel_evidence_record,
    write_panel_evidence_record,
)


def _case(project_root: Path) -> dict:
    return load_yaml(project_root / "cases/control-panel-evidence-records.example.yaml").data


def test_panel_evidence_record_is_safe_and_deterministic(project_root):
    case = _case(project_root)
    result = execute(case, live=False)
    record = build_panel_evidence_record(
        case,
        policy_decision="allowed",
        execution_mode="dry_run",
        tool=result.tool,
        request_count=result.request_count,
        response_metadata=result.response_metadata,
    )

    assert record["record_type"] == "service_control_panel_evidence_record"
    assert record["case_id"] == "control-panel-evidence-records"
    assert record["panel_alias"] == "example-admin-panel"
    assert record["target_alias"] == "local-placeholder"
    assert record["network_silent"] is True
    assert record["request_count"] == 0
    assert record["credential_material"] == "not_collected"
    assert record["screenshots"] == []
    assert record["captures"] == []
    assert record["finding_claims"] == []
    assert record["report_inclusion_status"] == "excluded_pending_review"
    assert record["planned_observations"] == case["requested_observations"]
    assert set(record["supported_observations"]) == PANEL_SAFE_OBSERVATIONS


def test_panel_evidence_rejects_report_ready_claims(project_root):
    case = _case(project_root)
    result = execute(case, live=False)
    record = build_panel_evidence_record(
        case,
        policy_decision="allowed",
        execution_mode="dry_run",
        tool=result.tool,
        request_count=result.request_count,
        response_metadata=result.response_metadata,
    )
    record["finding_claims"] = ["example finding claim"]

    try:
        validate_panel_evidence_record(record)
    except ValueError as exc:
        assert "finding claims" in str(exc)
    else:
        raise AssertionError("panel evidence accepted a finding claim")


def test_panel_evidence_file_registers_in_manifest(project_root, tmp_path):
    case = _case(project_root)
    result = execute(case, live=False)
    manifest = EvidenceManifest(
        run_id="run-panel-evidence-test",
        timestamp_utc="2000-01-01T00:00:00+00:00",
        operator="example-operator",
        sponsor_alias="example-sponsor",
        target_alias=case["target_alias"],
        authorization_reference="example-only",
        rules_of_engagement_reference="example-only",
        confidentiality_reference=None,
        case_id=case["id"],
        tool=result.tool,
        verifier_verdict="inconclusive",
        confidence="not_assessed",
        module_name=case["module"],
        artifact_mapping=list(case["evidence_mappings"]),
        target_category=case["target_category"],
        execution_mode="dry_run",
        policy_decision="allowed",
        request_count=result.request_count,
        response_metadata=result.response_metadata,
    )
    record_path = write_panel_evidence_record(
        case,
        tmp_path,
        policy_decision="allowed",
        execution_mode="dry_run",
        tool=result.tool,
        request_count=result.request_count,
        response_metadata=result.response_metadata,
    )
    artifact = register_artifact(
        manifest,
        tmp_path,
        record_path,
        role="service_control_panel_evidence_record",
        artifact_id="panel-evidence-record",
        redaction_status="passed",
    )
    assert artifact["path"] == PANEL_EVIDENCE_FILE
    manifest_path = write_manifest(manifest, tmp_path)

    loaded = load_manifest(manifest_path)
    assert loaded.artifacts[0]["artifact_id"] == "panel-evidence-record"
    assert verify_evidence_directory(tmp_path) == []


def test_cli_run_case_writes_panel_evidence_artifact(project_root, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    status = main(
        [
            "run-case",
            "--scope",
            str(project_root / "config/scope.panel-dry-run.example.yaml"),
            "--case",
            str(project_root / "cases/control-panel-evidence-records.example.yaml"),
            "--dry-run",
        ]
    )
    assert status == 0
    output = json.loads(capsys.readouterr().out)
    manifest_path = Path(output["evidence"])
    evidence_dir = manifest_path.parent
    record_path = evidence_dir / PANEL_EVIDENCE_FILE

    assert record_path.is_file()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["case_id"] == "control-panel-evidence-records"
    assert record["request_count"] == 0
    assert record["network_silent"] is True

    manifest = load_manifest(manifest_path)
    assert manifest.artifact_mapping == load_yaml(
        project_root / "cases/control-panel-evidence-records.example.yaml"
    ).data["evidence_mappings"]
    assert any(item["artifact_id"] == "panel-evidence-record" for item in manifest.artifacts)
    assert verify_evidence_directory(tmp_path / ".aotp" / "evidence") == []
