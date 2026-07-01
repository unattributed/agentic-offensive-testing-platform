from __future__ import annotations

from copy import deepcopy

import pytest

from aotp.adapter_examples import load_placeholder_examples, parse_placeholder_examples
from aotp.config import ConfigError, load_yaml


def _examples(project_root):
    return load_yaml(
        project_root / "examples/adapters/deferred-adapters.placeholder.yaml"
    ).data


def test_placeholder_examples_cover_every_deferred_adapter(project_root):
    plans = load_placeholder_examples(
        project_root / "examples/adapters/deferred-adapters.placeholder.yaml"
    )
    assert {plan.adapter_id for plan in plans} == {
        "browser-suite",
        "mitmproxy",
        "osmap",
        "playwright",
        "zap",
    }


def test_placeholder_examples_are_network_silent_and_non_executable(project_root):
    plans = load_placeholder_examples(
        project_root / "examples/adapters/deferred-adapters.placeholder.yaml"
    )
    for plan in plans:
        assert plan.plan_status == "placeholder_not_executable"
        assert plan.network_silent is True
        assert plan.live_execution_enabled is False
        assert plan.request_budget == 0
        assert all("://" not in value for value in plan.scope_field_aliases.values())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("execute", True, "must remain false"),
        ("request_budget", 1, "must remain zero"),
        ("execution_mode", "live", "must match"),
    ],
)
def test_placeholder_examples_reject_execution_enabling_fields(
    project_root,
    field,
    value,
    message,
):
    data = _examples(project_root)
    data["examples"][0][field] = value
    with pytest.raises(ConfigError, match=message):
        parse_placeholder_examples(data)


def test_placeholder_examples_reject_real_target_values(project_root):
    data = _examples(project_root)
    data["examples"][0]["scope_field_aliases"]["target_alias"] = (
        "https://target.example.invalid"
    )
    with pytest.raises(ConfigError, match="safe placeholder alias"):
        parse_placeholder_examples(data)


def test_placeholder_examples_reject_unsafe_example_id(project_root):
    data = _examples(project_root)
    data["examples"][0]["example_id"] = "https://target.example.invalid"
    with pytest.raises(ConfigError, match="safe placeholder alias"):
        parse_placeholder_examples(data)


@pytest.mark.parametrize("field", ["approval_requirements", "evidence_handling"])
def test_placeholder_examples_reject_duplicate_requirements(project_root, field):
    data = _examples(project_root)
    data["examples"][0][field].append(data["examples"][0][field][0])
    with pytest.raises(ConfigError, match="must be unique"):
        parse_placeholder_examples(data)


def test_placeholder_examples_reject_unsupported_capability(project_root):
    data = _examples(project_root)
    data["examples"][0]["requested_capabilities"].append("active_execution")
    with pytest.raises(ConfigError, match="unsupported capabilities"):
        parse_placeholder_examples(data)


def test_placeholder_examples_require_all_scope_boundaries(project_root):
    missing_scope = _examples(project_root)
    missing_scope["examples"][0]["scope_field_aliases"].pop("target_alias")
    with pytest.raises(ConfigError, match="cover required scope"):
        parse_placeholder_examples(missing_scope)


def test_placeholder_examples_require_all_approval_boundaries(project_root):
    missing_approval = deepcopy(_examples(project_root))
    missing_approval["examples"][0]["approval_requirements"].remove(
        "explicit_private_scope"
    )
    with pytest.raises(ConfigError, match="every requirement"):
        parse_placeholder_examples(missing_approval)


def test_placeholder_examples_require_each_adapter_once(project_root):
    data = _examples(project_root)
    data["examples"].pop()
    with pytest.raises(ConfigError, match="each adapter exactly once"):
        parse_placeholder_examples(data)
