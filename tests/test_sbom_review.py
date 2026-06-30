from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aotp.cli import main
from aotp.config import load_yaml
from aotp.evidence import EvidenceManifest, load_manifest, verify_evidence_directory, write_manifest
from aotp.finding_candidate import create_candidate
from aotp.finding_lifecycle import transition
from aotp.policy_gate import evaluate
from aotp.reporter import generate_markdown
from aotp.sbom_review import VULNERABILITY_MAPPING_CONTRACT, ingest_sbom_artifact
from aotp.verifier import create_verification, write_verification


def test_unprovided_and_escaped_artifacts_are_denied(project_root, example_scope, tmp_path):
    case = load_yaml(project_root / "cases/sbom-dependency-review.example.yaml").data
    outside = dict(case, artifact="../outside.json")
    decision = evaluate(example_scope, outside, workspace=tmp_path)
    assert not decision.allowed
    assert "SBOM or configuration artifact was not provided" in decision.reasons
    assert "provided artifact path must remain relative" in decision.reasons


def test_sbom_ingestion_is_reproducible_and_presence_only(project_root):
    path = project_root / "artifacts/sbom.placeholder.json"
    first = ingest_sbom_artifact(path, "artifacts/sbom.placeholder.json")
    second = ingest_sbom_artifact(path, "artifacts/sbom.placeholder.json")
    assert first == second
    assert first["artifact_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    component = first["components"][0]
    assert component["name"] == "placeholder-component"
    assert component["version"] == "0.0.0"
    assert component["presence"] == "observed"
    assert component["reachability"] == "not_assessed"
    assert component["exploitability"] == "not_assessed"
    assert component["vulnerability_mappings"] == []


def test_vulnerability_mapping_contract_is_offline():
    assert VULNERABILITY_MAPPING_CONTRACT["network_lookup"] is False
    assert VULNERABILITY_MAPPING_CONTRACT["automatic_exploitability_claims"] is False
    assert VULNERABILITY_MAPPING_CONTRACT["mode"] == "configured_local_data_source_only"


def test_cli_writes_verified_sbom_evidence_and_report_section(
    project_root,
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)
    status = main(
        [
            "run-case",
            "--scope",
            str(project_root / "config/scope.example.yaml"),
            "--case",
            str(project_root / "cases/sbom-dependency-review.example.yaml"),
            "--dry-run",
        ]
    )
    assert status == 0
    manifest_path = Path(json.loads(capsys.readouterr().out)["evidence"])
    manifest = load_manifest(manifest_path)
    assert manifest.sbom_artifact == "artifacts/sbom.placeholder.json"
    assert manifest.request_count == 0
    assert any(item["role"] == "sbom_component_evidence" for item in manifest.artifacts)
    assert verify_evidence_directory(tmp_path / ".aotp/evidence") == []
    report = generate_markdown(tmp_path / ".aotp/evidence")
    assert "Recorded SBOM components" in report
    assert "placeholder-component" in report
    assert "Presence: `observed`" in report
    assert "Reachability: `not_assessed`" in report
    assert "does not establish reachability or exploitability" in report


def test_component_presence_cannot_become_confirmed_risk(tmp_path):
    manifest = EvidenceManifest(
        run_id="sbom-presence",
        timestamp_utc="2026-07-01T00:00:00Z",
        operator="operator",
        sponsor_alias="sponsor",
        target_alias="target",
        authorization_reference="authorization",
        rules_of_engagement_reference="roe",
        confidentiality_reference=None,
        case_id="sbom-case",
        tool="offline-sbom-review",
        verifier_verdict="fail",
        confidence="medium",
        module_name="sbom_review",
    )
    evidence_path = write_manifest(manifest, tmp_path / "evidence")
    verification = create_verification(
        verdict="fail",
        confidence="medium",
        rationale="Component presence requires reachability review.",
        evidence_manifest_sha256=manifest.manifest_sha256 or "",
        evidence_references=["sbom-component-evidence"],
        verifier="human-reviewer",
    )
    verification_path = write_verification(
        verification,
        tmp_path / "evidence/verification.json",
    )
    candidate = create_candidate(
        evidence_path,
        verification_path,
        finding_id="component-presence",
        title="Component presence",
        summary="Presence only.",
        severity_candidate="low",
        evidence_strength="medium",
    )
    assert candidate.component_presence_only is True
    transition(candidate, "needs_human_review", reviewer="human-reviewer")
    with pytest.raises(ValueError, match="presence alone"):
        transition(
            candidate,
            "confirmed",
            reviewer="human-reviewer",
            human_validated=True,
        )
