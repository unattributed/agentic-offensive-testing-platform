import json

import yaml

from aotp.cli import main
from aotp.campaign import load_campaign
from aotp.campaign_loop import run_campaign
from aotp.evidence import sha256_file


def test_list_commands(capsys):
    assert main(["list-cases"]) == 0
    assert "wstg-authn-session.example.yaml" in capsys.readouterr().out
    assert main(["list-modules"]) == 0
    assert "bounded_fuzzing" in capsys.readouterr().out


def test_example_dry_run(project_root, monkeypatch):
    monkeypatch.chdir(project_root)
    assert main(["dry-run", "--scope", "config/scope.example.yaml"]) == 0


def test_live_cli_validates_private_documents_before_network_silent_stub(
    project_root,
    tmp_path,
    monkeypatch,
    authorized_scope,
    authorized_profile,
    authorized_approval,
    capsys,
):
    scope_path = tmp_path / "private-scope.yaml"
    profile_path = tmp_path / "private-profile.yaml"
    approval_path = tmp_path / "private-approval.yaml"
    scope_path.write_text(yaml.safe_dump(authorized_scope, sort_keys=False), encoding="utf-8")
    profile_path.write_text(yaml.safe_dump(authorized_profile, sort_keys=False), encoding="utf-8")
    authorized_approval["scope_sha256"] = sha256_file(scope_path)
    authorized_approval["objective_ids"] = ["wstg-security-headers"]
    approval_path.write_text(yaml.safe_dump(authorized_approval, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = main(
        [
            "run-case",
            "--scope",
            str(scope_path),
            "--case",
            str(project_root / "cases/wstg-security-headers.example.yaml"),
            "--program-profile",
            str(profile_path),
            "--approval",
            str(approval_path),
            "--live",
            "--operator-approved",
        ]
    )

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["allowed"] is True
    evidence = json.loads(next((tmp_path / ".aotp/evidence").rglob("evidence.json")).read_text())
    assert evidence["tool"] == "live-adapter-stub"
    assert evidence["verifier_verdict"] == "manual_review"
    assert evidence["request_count"] == 0


def test_policy_check_is_a_non_executing_live_preflight(
    project_root,
    tmp_path,
    monkeypatch,
    authorized_scope,
    authorized_profile,
    authorized_approval,
    capsys,
):
    scope_path = tmp_path / "private-scope.yaml"
    profile_path = tmp_path / "private-profile.yaml"
    approval_path = tmp_path / "private-approval.yaml"
    scope_path.write_text(yaml.safe_dump(authorized_scope, sort_keys=False), encoding="utf-8")
    profile_path.write_text(yaml.safe_dump(authorized_profile, sort_keys=False), encoding="utf-8")
    authorized_approval["scope_sha256"] = sha256_file(scope_path)
    authorized_approval["objective_ids"] = ["wstg-security-headers"]
    approval_path.write_text(yaml.safe_dump(authorized_approval, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = main(
        [
            "policy-check",
            "--scope",
            str(scope_path),
            "--case",
            str(project_root / "cases/wstg-security-headers.example.yaml"),
            "--program-profile",
            str(profile_path),
            "--approval",
            str(approval_path),
            "--live",
            "--operator-approved",
        ]
    )

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "allowed": True,
        "mode": "live",
        "scope_id": "example-dry-run",
        "case_id": "wstg-security-headers",
        "reasons": [],
    }
    assert not (tmp_path / ".aotp").exists()


def test_campaign_resume_cli_applies_bound_review_and_continues(
    project_root,
    tmp_path,
    monkeypatch,
    example_scope,
    capsys,
):
    scope_path = project_root / "config/scope.example.yaml"
    campaign_path = project_root / "campaigns/bug-bounty-efficiency-campaign.example.yaml"
    campaign = load_campaign(str(campaign_path)).data
    state, state_path = run_campaign(
        example_scope,
        scope_path,
        campaign,
        workspace=tmp_path,
    )
    review = {
        "schema_version": "1.0",
        "decision_id": "cli-review-approved",
        "campaign_id": state.campaign_id,
        "objective_id": state.current_objective_id,
        "operator_alias": state.operator_alias,
        "decision": "approved",
        "decided_at_utc": "2026-06-30T00:00:00Z",
        "state_sha256": sha256_file(state_path),
        "reason": "synthetic CLI resume test",
    }
    review_path = tmp_path / "private-review.yaml"
    review_path.write_text(yaml.safe_dump(review), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = main(
        [
            "campaign-resume",
            "--state",
            str(state_path),
            "--scope",
            str(scope_path),
            "--campaign",
            str(campaign_path),
            "--review",
            str(review_path),
        ]
    )

    assert result == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"
