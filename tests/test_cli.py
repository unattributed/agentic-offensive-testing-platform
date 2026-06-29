import json

import yaml

from aotp.cli import main
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
