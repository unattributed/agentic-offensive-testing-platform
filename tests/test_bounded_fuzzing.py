from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from aotp.bounded_fuzzing import (
    FUZZING_STOP_SIGNALS,
    FUZZING_UNSAFE_ACTIONS,
    FuzzingRequestBudget,
    build_corpus_reference,
    build_fuzzing_dry_run_plan,
)
from aotp.campaign import parse_campaign
from aotp.campaign_loop import run_campaign
from aotp.cli import main
from aotp.config import ConfigError, load_yaml
from aotp.evidence import load_manifest, verify_evidence_directory
from aotp.executor import execute
from aotp.policy_gate import evaluate


def _case(project_root: Path) -> dict:
    case = load_yaml(project_root / "cases/bounded-fuzzing.example.yaml").data
    case["human_approved"] = True
    return case


def _scope(example_scope: dict) -> dict:
    scope = deepcopy(example_scope)
    scope["fuzzing"].update(
        {
            "authorized": True,
            "approved_actions": ["plan_bounded_fuzzing"],
            "denied_actions": sorted(FUZZING_UNSAFE_ACTIONS),
        }
    )
    return scope


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("payload_count", 0, "payload_count must be a positive integer"),
        ("payload_count", 2, "exceeds scope payload_budget"),
        ("max_response_bytes", 65537, "max_response_bytes exceeds scope limit"),
        ("max_retries", 1, "max_retries exceeds scope limit"),
        ("max_runtime_seconds", 2, "max_runtime_seconds exceeds scope limit"),
    ],
)
def test_fuzzing_objective_limits_fail_closed(
    project_root,
    example_scope,
    tmp_path,
    field,
    value,
    reason,
):
    case = _case(project_root)
    case[field] = value
    decision = evaluate(_scope(example_scope), case, workspace=tmp_path)
    assert not decision.allowed
    assert any(reason in item for item in decision.reasons)


def test_unsafe_payload_class_is_denied(project_root, example_scope, tmp_path):
    case = _case(project_root)
    case["payload_classes"] = ["command_injection"]
    decision = evaluate(_scope(example_scope), case, workspace=tmp_path)
    assert not decision.allowed
    assert "fuzzing payload class is not approved as safe: command_injection" in decision.reasons


def test_endpoint_and_total_plans_cannot_exceed_scope(
    project_root,
    example_scope,
    tmp_path,
):
    case = _case(project_root)
    case["endpoint_request_budgets"] = {"endpoint-a": 2}
    decision = evaluate(_scope(example_scope), case, workspace=tmp_path)
    assert not decision.allowed
    assert any("per_endpoint_limit" in item for item in decision.reasons)

    scope = _scope(example_scope)
    scope["fuzzing"]["request_budget"] = 2
    scope["fuzzing"]["per_endpoint_limit"] = 2
    case["endpoint_request_budgets"] = {"endpoint-a": 2, "endpoint-b": 1}
    decision = evaluate(scope, case, workspace=tmp_path)
    assert not decision.allowed
    assert "fuzzing planned requests exceed scope request_budget" in decision.reasons


def test_request_budget_counter_refuses_overruns():
    budget = FuzzingRequestBudget(total_limit=2, per_endpoint_limit=1)
    budget.reserve("endpoint-a")
    assert budget.total_requests == 1
    assert budget.endpoint_requests == {"endpoint-a": 1}
    with pytest.raises(ValueError, match="per-endpoint"):
        budget.reserve("endpoint-a")
    budget.reserve("endpoint-b")
    with pytest.raises(ValueError, match="total"):
        budget.reserve("endpoint-c")
    with pytest.raises(ValueError, match="cannot exceed"):
        FuzzingRequestBudget(total_limit=1, per_endpoint_limit=2)


def test_fuzzing_dry_run_is_deterministic_and_network_silent(project_root):
    case = _case(project_root)
    first = build_fuzzing_dry_run_plan(case)
    second = build_fuzzing_dry_run_plan(case)
    assert first == second
    assert first["planned_request_count"] == 1
    assert first["request_count"] == 0
    assert first["network_silent"] is True
    assert first["payload_values"] == "not_recorded"

    result = execute(case)
    assert result.tool == "bounded-fuzzing-dry-run-planner"
    assert result.request_count == 0
    assert result.response_metadata["fuzzing_plan"] == first

    stopped = deepcopy(case)
    stopped["detected_stop_signals"] = ["target_instability"]
    with pytest.raises(ValueError, match="stop condition detected"):
        build_fuzzing_dry_run_plan(stopped)


def test_private_corpus_reference_contains_hash_not_payloads(tmp_path):
    corpus = tmp_path / "private-corpus.txt"
    corpus.write_text("first-private-payload\nsecond-private-payload\n", encoding="utf-8")
    reference = build_corpus_reference(
        corpus,
        alias="private-corpus",
        payload_class="boundary_value",
    )
    assert reference["sha256"] == hashlib.sha256(corpus.read_bytes()).hexdigest()
    assert reference["payload_count"] == 2
    encoded = json.dumps(reference)
    assert "first-private-payload" not in encoded
    assert str(corpus) not in encoded


def test_cli_corpus_reference_and_fuzzing_evidence(
    project_root,
    example_scope,
    tmp_path,
    monkeypatch,
    capsys,
):
    corpus = tmp_path / "private-corpus.txt"
    corpus.write_text("private-payload\n", encoding="utf-8")
    reference_path = tmp_path / "corpus-reference.json"
    status = main(
        [
            "fuzzing-corpus-reference",
            "--corpus",
            str(corpus),
            "--alias",
            "private-corpus",
            "--payload-class",
            "boundary_value",
            "--output",
            str(reference_path),
        ]
    )
    assert status == 0
    capsys.readouterr()
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    assert reference_path.stat().st_mode & 0o777 == 0o600

    scope = _scope(example_scope)
    scope_path = tmp_path / "scope.yaml"
    scope_path.write_text(yaml.safe_dump(scope, sort_keys=False), encoding="utf-8")
    case = _case(project_root)
    case.pop("human_approved")
    case["requires_human_approval"] = False
    case["corpus_reference"] = reference
    case_path = tmp_path / "case.yaml"
    case_path.write_text(yaml.safe_dump(case, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    status = main(
        [
            "run-case",
            "--scope",
            str(scope_path),
            "--case",
            str(case_path),
            "--dry-run",
        ]
    )
    assert status == 0
    output = json.loads(capsys.readouterr().out)
    manifest_path = Path(output["evidence"])
    manifest = load_manifest(manifest_path)
    assert manifest.request_count == 0
    assert manifest.fuzzing_corpus_reference == "private-corpus"
    assert any(
        artifact["role"] == "bounded_fuzzing_evidence_record"
        for artifact in manifest.artifacts
    )
    record = json.loads(
        (manifest_path.parent / "fuzzing-evidence.json").read_text(encoding="utf-8")
    )
    assert record["payload_values"] == "not_recorded"
    assert record["corpus_reference"] == reference
    assert verify_evidence_directory(tmp_path / ".aotp" / "evidence") == []


def test_bounded_fuzzing_campaign_writes_zero_request_counters(
    project_root,
    example_scope,
    tmp_path,
):
    campaign = load_yaml(
        project_root / "campaigns/bounded-fuzzing-campaign.example.yaml"
    ).data
    campaign["objectives"][0]["requires_human_approval"] = False
    state, _ = run_campaign(
        _scope(example_scope),
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    assert state.current_status == "completed"
    assert state.request_counters["total"] == 0
    assert state.endpoint_request_counters == {"placeholder-api-root": 0}
    evidence_dir = tmp_path / state.evidence_directories[0]
    assert (evidence_dir / "fuzzing-evidence.json").is_file()
    assert verify_evidence_directory(evidence_dir) == []


def test_runnable_fuzzing_example_scope_and_campaign(project_root, tmp_path):
    scope = load_yaml(
        project_root / "config/scope.fuzzing-dry-run.example.yaml"
    ).data
    campaign = load_yaml(
        project_root / "campaigns/bounded-fuzzing-campaign.example.yaml"
    ).data
    state, _ = run_campaign(
        scope,
        project_root / "config/scope.fuzzing-dry-run.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    assert state.current_status == "completed"
    assert state.request_counters == {"total": 0}


def test_fuzzing_stop_signals_persist_events_and_counters(
    project_root,
    example_scope,
    tmp_path,
):
    campaign = load_yaml(
        project_root / "campaigns/bounded-fuzzing-campaign.example.yaml"
    ).data
    campaign["campaign_id"] = "example-bounded-fuzzing-stop"
    campaign["objectives"][0]["detected_stop_signals"] = [
        "target_instability",
        "response_size_limit",
    ]
    state, _ = run_campaign(
        _scope(example_scope),
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    assert state.current_status == "stopped_by_condition"
    assert state.request_counters["total"] == 0
    assert state.endpoint_request_counters == {}
    assert state.stop_condition_history == [
        "response_size_limit",
        "target_instability",
    ]
    stop_event = [
        event for event in state.events if event["event_type"] == "campaign_stop"
    ][-1]
    assert stop_event["details"]["request_counters"] == {"total": 0}
    assert stop_event["details"]["endpoint_request_counters"] == {}
    manifest = load_manifest(
        tmp_path / state.evidence_directories[0] / "evidence.json"
    )
    assert manifest.request_count == 0
    assert manifest.response_metadata["stop_conditions"] == [
        "response_size_limit",
        "target_instability",
    ]


@pytest.mark.parametrize("signal", sorted(FUZZING_STOP_SIGNALS))
def test_each_supported_fuzzing_stop_signal_stops_before_execution(
    project_root,
    example_scope,
    tmp_path,
    signal,
):
    campaign = load_yaml(
        project_root / "campaigns/bounded-fuzzing-campaign.example.yaml"
    ).data
    campaign["campaign_id"] = f"example-fuzzing-stop-{signal}"
    campaign["objectives"][0]["detected_stop_signals"] = [signal]
    state, _ = run_campaign(
        _scope(example_scope),
        project_root / "config/scope.example.yaml",
        campaign,
        workspace=tmp_path,
    )
    assert state.current_status == "stopped_by_condition"
    assert state.stop_condition_history == [signal]
    assert state.request_counters == {"total": 0}


def test_fuzzing_campaign_requires_all_safety_stops(project_root):
    campaign = load_yaml(
        project_root / "campaigns/bounded-fuzzing-campaign.example.yaml"
    ).data
    campaign["stop_conditions"].remove("retry_limit")
    with pytest.raises(ConfigError, match="retry_limit"):
        parse_campaign(campaign)
