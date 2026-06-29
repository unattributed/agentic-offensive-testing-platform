from pathlib import Path

from aotp.policy_gate import evaluate


def test_missing_scope_is_denied():
    decision = evaluate(None)
    assert not decision.allowed
    assert "scope is missing" in decision.reasons


def test_example_scope_allows_network_silent_dry_run(example_scope, tmp_path):
    decision = evaluate(example_scope, workspace=tmp_path)
    assert decision.allowed


def test_example_scope_denies_live_mode(example_scope, tmp_path):
    decision = evaluate(example_scope, live=True, operator_approved=True, workspace=tmp_path)
    assert not decision.allowed
    assert "live mode lacks explicit live authorization" in decision.reasons


def test_target_expansion_is_denied(example_scope, tmp_path):
    objective = {"target_alias": "unlisted", "category": "wstg_webapp"}
    assert not evaluate(example_scope, objective, workspace=tmp_path).allowed


def test_forbidden_action_is_denied(example_scope, tmp_path):
    objective = {"target_alias": "local-placeholder", "category": "wstg_webapp", "action": "credential_attack"}
    assert not evaluate(example_scope, objective, workspace=tmp_path).allowed


def test_fuzzing_requires_explicit_authorization(example_scope, tmp_path):
    objective = {"target_alias": "local-placeholder", "category": "bounded_fuzzing", "action": "active_fuzzing"}
    decision = evaluate(example_scope, objective, workspace=tmp_path)
    assert not decision.allowed
    assert "fuzzing is not explicitly authorized" in decision.reasons


def test_service_and_api_must_be_allowlisted(example_scope, tmp_path):
    objective = {
        "target_alias": "local-placeholder",
        "category": "wstg_webapp",
        "service": "unlisted",
        "api": "unlisted",
    }
    decision = evaluate(example_scope, objective, workspace=tmp_path)
    assert not decision.allowed
    assert "service is not explicitly allowlisted" in decision.reasons
    assert "API is not explicitly allowlisted" in decision.reasons


def test_evidence_directory_cannot_escape_workspace(example_scope, tmp_path):
    example_scope["evidence"]["workspace"] = str(Path(tmp_path).parent / "outside")
    decision = evaluate(example_scope, workspace=tmp_path)
    assert not decision.allowed
    assert "evidence directory is outside the configured workspace" in decision.reasons


def test_human_approval_and_redaction_fail_closed(example_scope, tmp_path):
    objective = {"target_alias": "local-placeholder", "category": "wstg_webapp", "requires_human_approval": True}
    decision = evaluate(example_scope, objective, workspace=tmp_path, redaction_passed=False)
    assert not decision.allowed
    assert "human approval is required" in decision.reasons
    assert "redaction checks failed" in decision.reasons
