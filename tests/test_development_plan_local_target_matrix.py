from pathlib import Path


def test_development_plan_includes_sprint18h_local_target_matrix() -> None:
    plan = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "## Sprint 18H: Local Vulnerable Target Matrix" in plan
    assert "local target matrix registry" in plan
    assert "OWASP crAPI" in plan
    assert "first additional planned target" in plan
    assert "live runtime pending" in plan
    assert "without making crAPI a dependency of the WSTG engine" in plan
