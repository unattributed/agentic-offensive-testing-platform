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
    assert "private program profile is missing" in decision.reasons


def test_complete_live_authorization_relationship_is_allowed(
    authorized_scope,
    authorized_profile,
    authorized_approval,
    authorized_scope_sha256,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        operator_approval=authorized_approval,
        scope_sha256=authorized_scope_sha256,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert decision.allowed, decision.reasons


def test_live_execution_requires_private_approval_record(
    authorized_scope,
    authorized_profile,
    authorized_scope_sha256,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        scope_sha256=authorized_scope_sha256,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "private operator approval record is missing" in decision.reasons


def test_approval_must_match_scope_and_objective(
    authorized_scope,
    authorized_profile,
    authorized_approval,
    authorized_scope_sha256,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_approval["scope_sha256"] = "c" * 64
    authorized_approval["objective_ids"] = ["different-objective"]
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        operator_approval=authorized_approval,
        scope_sha256=authorized_scope_sha256,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "operator approval scope SHA256 does not match scope file" in decision.reasons
    assert "operator approval does not cover this objective or campaign" in decision.reasons


def test_expired_operator_approval_is_denied(
    authorized_scope,
    authorized_profile,
    authorized_approval,
    authorized_scope_sha256,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_approval["valid_until_utc"] = "2026-06-01T00:00:00Z"
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        operator_approval=authorized_approval,
        scope_sha256=authorized_scope_sha256,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "operator approval has expired" in decision.reasons


def test_live_execution_requires_an_active_test_window(
    authorized_scope,
    authorized_profile,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_scope["allowed_test_windows"][0].update(
        {"start_utc": "2026-01-01T00:00:00Z", "end_utc": "2026-06-01T00:00:00Z"}
    )
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "current time is outside all allowed test windows" in decision.reasons


def test_rules_of_engagement_must_match_accepted_policy(
    authorized_scope,
    authorized_profile,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_scope["rules_of_engagement"]["policy_sha256"] = "b" * 64
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "rules-of-engagement policy SHA256 does not match program profile" in decision.reasons


def test_live_execution_requires_all_safety_stops(
    authorized_scope,
    authorized_profile,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_scope["stop_conditions"].remove("authentication_lockout_risk")
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert any(reason.startswith("required stop conditions are missing") for reason in decision.reasons)


def test_automatic_report_submission_is_denied(
    authorized_scope,
    authorized_profile,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_scope["reporting"]["automatic_submission"] = True
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "automatic report submission is forbidden" in decision.reasons


def test_live_profile_must_match_scope_and_authorization(
    authorized_scope,
    authorized_profile,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_profile["program_alias"] = "different-program"
    authorized_profile["authorization_reference"] = "different-authorization"
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "program profile alias does not match scope" in decision.reasons
    assert "authorization reference does not match program profile" in decision.reasons


def test_expired_live_authorization_is_denied(
    authorized_scope,
    authorized_profile,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_scope["authorization"]["valid_until_utc"] = "2026-06-01T00:00:00Z"
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "authorization has expired" in decision.reasons


def test_program_profile_out_of_scope_and_category_rules_are_authoritative(
    authorized_scope,
    authorized_profile,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_profile["in_scope_asset_aliases"] = ["different-asset"]
    authorized_profile["out_of_scope_asset_aliases"] = ["local-placeholder"]
    authorized_profile["allowed_testing_categories"] = ["sbom_review"]
    authorized_profile["forbidden_testing_categories"] = ["wstg_webapp"]
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "target is explicitly out of scope in program profile" in decision.reasons
    assert "test category is forbidden by program profile" in decision.reasons


def test_live_rate_limit_cannot_exceed_program_limit(
    authorized_scope,
    authorized_profile,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_scope["rate_limits"]["requests_per_minute"] = 2
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "scope rate limit exceeds program profile limit" in decision.reasons


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


def test_environment_and_account_must_be_allowlisted(example_scope, tmp_path):
    objective = {
        "target_alias": "local-placeholder",
        "category": "wstg_webapp",
        "environment": "unlisted",
        "account_alias": "unlisted",
    }
    decision = evaluate(example_scope, objective, workspace=tmp_path)
    assert not decision.allowed
    assert "environment is not explicitly allowlisted" in decision.reasons
    assert "test account is not explicitly approved" in decision.reasons


def test_live_network_domain_must_be_explicitly_allowlisted(
    authorized_scope,
    authorized_profile,
    authorized_approval,
    authorized_scope_sha256,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_objective["domain"] = "outside.invalid"
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        operator_approval=authorized_approval,
        scope_sha256=authorized_scope_sha256,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "domain is not explicitly allowlisted" in decision.reasons


def test_wildcard_domain_does_not_implicitly_include_apex(
    authorized_scope,
    authorized_profile,
    authorized_approval,
    authorized_scope_sha256,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_scope["allowed_targets"][0]["domains"] = ["*.example.invalid"]
    authorized_objective["domain"] = "example.invalid"
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        operator_approval=authorized_approval,
        scope_sha256=authorized_scope_sha256,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "domain is not explicitly allowlisted" in decision.reasons


def test_wildcard_domain_allows_only_a_real_subdomain(
    authorized_scope,
    authorized_profile,
    authorized_approval,
    authorized_scope_sha256,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_scope["allowed_targets"][0]["domains"] = ["*.example.invalid"]
    authorized_objective["domain"] = "app.example.invalid"
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        operator_approval=authorized_approval,
        scope_sha256=authorized_scope_sha256,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert decision.allowed, decision.reasons


def test_placeholder_authorization_reference_is_denied(
    authorized_scope,
    authorized_profile,
    authorized_approval,
    authorized_scope_sha256,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_scope["authorization"]["reference"] = "replace-me"
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        operator_approval=authorized_approval,
        scope_sha256=authorized_scope_sha256,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "authorization reference is missing" in decision.reasons


def test_required_confidentiality_confirmation_is_enforced(
    authorized_scope,
    authorized_profile,
    authorized_approval,
    authorized_scope_sha256,
    authorized_objective,
    authorized_now,
    tmp_path,
):
    authorized_scope["authorization"]["confidentiality"] = {
        "required": True,
        "confirmed": False,
        "reference": None,
    }
    decision = evaluate(
        authorized_scope,
        authorized_objective,
        program_profile=authorized_profile,
        operator_approval=authorized_approval,
        scope_sha256=authorized_scope_sha256,
        live=True,
        operator_approved=True,
        workspace=tmp_path,
        now=authorized_now,
    )
    assert not decision.allowed
    assert "required confidentiality confirmation is missing" in decision.reasons


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
