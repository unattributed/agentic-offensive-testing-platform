from __future__ import annotations

import ast
import inspect
from pathlib import Path

from aotp.adapters.ollama_adapter import OllamaAdapter
from aotp.capability_registry import list_adapters
from aotp.executor import execute
from aotp.reporter import generate_markdown


def _execution_calls_are_policy_guarded(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    evaluate_lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "evaluate"
    ]
    execute_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "execute"
    ]
    assert evaluate_lines
    assert execute_calls
    for call in execute_calls:
        assert min(evaluate_lines) < call.lineno
        current: ast.AST | None = call
        guarded = False
        while current in parents:
            current = parents[current]
            if isinstance(current, (ast.If, ast.IfExp)):
                if ast.unparse(current.test) == "decision.allowed":
                    guarded = True
                    break
        assert guarded, f"executor call at {path}:{call.lineno} bypasses decision.allowed"


def test_every_executor_call_is_nested_under_policy_allow(project_root):
    _execution_calls_are_policy_guarded(project_root / "src/aotp/cli.py")
    _execution_calls_are_policy_guarded(project_root / "src/aotp/campaign_loop.py")


def test_only_cli_and_campaign_loop_import_executor(project_root):
    importers = []
    for path in (project_root / "src/aotp").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "executor":
                if any(alias.name == "execute" for alias in node.names):
                    importers.append(path.relative_to(project_root).as_posix())
    assert sorted(importers) == ["src/aotp/campaign_loop.py", "src/aotp/cli.py"]


def test_live_executor_boundary_is_a_zero_request_manual_review_stub():
    result = execute({"action": "placeholder"}, live=True)
    assert result.tool == "live-adapter-stub"
    assert result.request_count == 0
    assert result.verdict == "manual_review"
    assert "no network request was sent" in result.response_metadata["status"]


def test_models_and_deferred_adapters_have_no_authority():
    model = OllamaAdapter()
    assert {"scope_authorization", "policy_override"}.issubset(model.denies)
    for adapter in list_adapters():
        assert adapter["live_execution_enabled"] is False
        assert adapter["network_silent_default"] is True
        assert adapter["default_request_budget"] == 0
        assert "explicit_private_scope" in adapter["required_approvals"]
        assert "policy_gate_approval" in adapter["required_approvals"]


def test_reporter_accepts_only_evidence_and_finding_paths():
    assert tuple(inspect.signature(generate_markdown).parameters) == (
        "evidence_directory",
        "findings_directory",
    )


def test_langgraph_delegates_to_deterministic_campaign_loop(project_root):
    source = (
        project_root / "src/aotp/langgraph_orchestration.py"
    ).read_text(encoding="utf-8")
    assert "from .campaign_loop import run_campaign" in source
    assert "from .executor import execute" not in source
    assert "run_campaign(" in source
