from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from aotp.cli import main
from aotp.config import load_yaml
from aotp.crypto_review import build_crypto_record
from aotp.evidence import EvidenceManifest, write_manifest
from aotp.finding_candidate import create_candidate
from aotp.finding_lifecycle import transition
from aotp.policy_gate import evaluate
from aotp.reporter import generate_markdown
from aotp.verifier import create_verification, write_verification


def _case(project_root: Path) -> dict:
    return load_yaml(project_root / "cases/cryptographic-controls-review.example.yaml").data


def _scope(example_scope: dict) -> dict:
    scope = deepcopy(example_scope)
    scope["cryptographic_controls"] = {
        "authorized": True,
        "approved_actions": ["inspect_provided_crypto_evidence"],
        "denied_actions": [
            "destructive_crypto_testing",
            "private_key_extraction",
            "secret_bruteforce",
        ],
    }
    return scope


def test_crypto_policy_requires_explicit_action(project_root, example_scope, tmp_path):
    case = _case(project_root)
    assert not evaluate(example_scope, case, workspace=tmp_path).allowed
    assert evaluate(_scope(example_scope), case, workspace=tmp_path).allowed
    case["action"] = "private_key_extraction"
    decision = evaluate(_scope(example_scope), case, workspace=tmp_path)
    assert not decision.allowed
    assert any("explicitly denied" in reason for reason in decision.reasons)


def test_crypto_record_contains_metadata_without_private_material(project_root):
    record = build_crypto_record(_case(project_root))
    assert record["tls_evidence"]["protocol"] == "TLSv1.2"
    assert record["cookie_attributes"][0]["secure"] is True
    assert record["token_configuration"]["algorithm"] == "RS256"
    assert record["key_management_metadata"]["private_material_present"] is False
    assert record["private_material"] == "not_collected"
    assert record["request_count"] == 0


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("cookie_attributes", "value", "secret-cookie-value"),
        ("token_configuration", "secret", "secret-token-value"),
        ("key_management_metadata", "private_key", "private-key-material"),
    ],
)
def test_secret_fields_fail_closed(project_root, section, field, value):
    case = _case(project_root)
    if section == "cookie_attributes":
        case[section][0][field] = value
    else:
        case[section][field] = value
    with pytest.raises(ValueError, match="forbidden|attributes only"):
        build_crypto_record(case)


def test_cli_writes_crypto_evidence_and_uncertainty_report(
    project_root,
    example_scope,
    tmp_path,
    monkeypatch,
    capsys,
):
    scope_path = tmp_path / "scope.yaml"
    scope_path.write_text(yaml.safe_dump(_scope(example_scope)), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    status = main(
        [
            "run-case",
            "--scope",
            str(scope_path),
            "--case",
            str(project_root / "cases/cryptographic-controls-review.example.yaml"),
            "--dry-run",
        ]
    )
    assert status == 0
    manifest_path = Path(json.loads(capsys.readouterr().out)["evidence"])
    assert (manifest_path.parent / "crypto-evidence.json").is_file()
    report = generate_markdown(tmp_path / ".aotp/evidence")
    assert "Recorded cryptographic controls" in report
    assert "TLS protocol: `TLSv1.2`" in report
    assert "Private material: `not_collected`" in report
    assert "not confirmed weaknesses" in report


def test_weak_indicator_cannot_be_confirmed_without_verified_evidence(tmp_path):
    record = {
        "weak_algorithm_indicators": [
            {"indicator": "legacy-signature", "status": "observation_only"}
        ]
    }
    manifest = EvidenceManifest(
        run_id="crypto-indicator",
        timestamp_utc="2026-07-01T00:00:00Z",
        operator="operator",
        sponsor_alias="sponsor",
        target_alias="target",
        authorization_reference="authorization",
        rules_of_engagement_reference="roe",
        confidentiality_reference=None,
        case_id="crypto-case",
        tool="offline-crypto-controls-review",
        verifier_verdict="fail",
        confidence="medium",
        module_name="crypto_controls",
        response_metadata={"crypto_record": record},
    )
    evidence_path = write_manifest(manifest, tmp_path / "evidence")
    verification = create_verification(
        verdict="fail",
        confidence="medium",
        rationale="Indicator requires human evidence review.",
        evidence_manifest_sha256=manifest.manifest_sha256 or "",
        evidence_references=["crypto-controls-evidence"],
        verifier="human-reviewer",
    )
    verification_path = write_verification(
        verification,
        tmp_path / "evidence/verification.json",
    )
    candidate = create_candidate(
        evidence_path,
        verification_path,
        finding_id="crypto-indicator",
        title="Cryptographic indicator",
        summary="Observation only.",
        severity_candidate="low",
        evidence_strength="medium",
    )
    assert candidate.crypto_indicator_only is True
    transition(candidate, "needs_human_review", reviewer="human-reviewer")
    with pytest.raises(ValueError, match="verified evidence"):
        transition(
            candidate,
            "confirmed",
            reviewer="human-reviewer",
            human_validated=True,
        )
