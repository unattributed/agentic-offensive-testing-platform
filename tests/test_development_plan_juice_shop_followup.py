from pathlib import Path


def test_development_plan_includes_sprint18_juice_shop_followup() -> None:
    plan = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "## Sprint 18F: Local Juice Shop WSTG Campaign Benchmark" in plan
    assert "loopback-only OWASP Juice Shop" in plan
    assert "scripts/juice-shop-local-reset.sh" in plan
    assert "local Juice Shop benchmark fixtures" in plan
    assert "OSMAP benchmark fixtures" not in plan
