from aotp.cli import main


def test_list_commands(capsys):
    assert main(["list-cases"]) == 0
    assert "wstg-authn-session.example.yaml" in capsys.readouterr().out
    assert main(["list-modules"]) == 0
    assert "bounded_fuzzing" in capsys.readouterr().out


def test_example_dry_run(project_root, monkeypatch):
    monkeypatch.chdir(project_root)
    assert main(["dry-run", "--scope", "config/scope.example.yaml"]) == 0
