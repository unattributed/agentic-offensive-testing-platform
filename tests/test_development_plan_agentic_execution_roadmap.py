from pathlib import Path


def test_development_plan_prioritizes_agentic_execution_depth() -> None:
    plan = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "real tests" in plan
    assert "vetted and validated findings" in plan
    assert "Generic Agentic WSTG Execution Harness" in plan
    assert "Stateful Browser Workflows and Authenticated Sessions" in plan
    assert "Form Discovery, API Discovery, and Controlled Action Chains" in plan
    assert "Evidence-Driven Proof Requests and Finding Validation" in plan
    assert "Validated Finding Packages and Professional Assessment Reporting" in plan
    assert "Authorized External Campaign Readiness" in plan


def test_development_plan_defers_new_targets_and_marks_crapi_pending() -> None:
    plan = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "No more local vulnerable targets are planned" in plan
    assert "Juice Shop is the active local live benchmark" in plan
    assert "OWASP crAPI is a planned registered target" in plan
    assert "live runtime pending" in plan
    assert "without making crAPI a dependency of the WSTG engine" in plan


def test_development_plan_requires_professional_reportable_findings() -> None:
    plan = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "A finding can become reportable only after it passes a lifecycle gate" in plan
    assert "validated -> report_ready" in plan
    assert "false-positive checks performed" in plan
    assert "manual-only disclosure" in plan
    assert "professional campaign assessment reports" in plan
