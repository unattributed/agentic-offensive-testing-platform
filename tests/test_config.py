import pytest

from copy import deepcopy

from aotp.config import (
    ConfigError,
    load_yaml,
    parse_operator_approval,
    parse_program_profile,
    parse_scope,
    validate_scope_shape,
)


def test_example_scope_is_structurally_valid(project_root):
    loaded = load_yaml(project_root / "config/scope.example.yaml")
    validate_scope_shape(loaded.data)
    scope = parse_scope(loaded.data)
    assert scope.program_alias == "example-program"
    assert scope.target("local-placeholder").approved_account_aliases == ("provisioned-example-account",)


def test_example_program_profile_is_structurally_valid(project_root):
    loaded = load_yaml(project_root / "config/program-profile.example.yaml")
    profile = parse_program_profile(loaded.data)
    assert profile.program_alias == "example-program"
    assert profile.in_scope_asset_aliases == ("local-placeholder",)


def test_scope_rejects_unknown_fields(example_scope):
    example_scope["allow_target_expansion"] = True
    with pytest.raises(ConfigError, match="unknown fields"):
        parse_scope(example_scope)


def test_scope_rejects_duplicate_target_aliases(example_scope):
    duplicate = deepcopy(example_scope["allowed_targets"][0])
    example_scope["allowed_targets"].append(duplicate)
    with pytest.raises(ConfigError, match="must not contain duplicates"):
        parse_scope(example_scope)


def test_program_profile_rejects_scope_contradictions(project_root):
    profile = load_yaml(project_root / "config/program-profile.example.yaml").data
    profile["out_of_scope_asset_aliases"] = ["local-placeholder"]
    with pytest.raises(ConfigError, match="both in and out of scope"):
        parse_program_profile(profile)


def test_operator_approval_example_is_structurally_valid(project_root):
    approval = load_yaml(project_root / "config/operator-approval.example.yaml").data
    parsed = parse_operator_approval(approval)
    assert parsed.decision == "denied"
    assert parsed.objective_ids == ("example-only",)


def test_missing_config_fails_closed(tmp_path):
    with pytest.raises(ConfigError):
        load_yaml(tmp_path / "missing.yaml")
