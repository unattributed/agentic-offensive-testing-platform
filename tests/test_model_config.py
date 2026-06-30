from __future__ import annotations

from copy import deepcopy

import pytest

from aotp.config import ConfigError, load_yaml
from aotp.model_config import (
    LocalModelConfig,
    load_local_model_config,
    parse_local_model_config,
)


def _config(project_root):
    return load_yaml(project_root / "config/models.example.yaml").data


def test_example_model_config_is_local_structured_and_allowlisted(project_root):
    config = load_local_model_config(project_root / "config/models.example.yaml")
    assert config.base_url == "http://localhost:11434"
    assert config.approves(config.default_model)
    assert config.structured_json is True
    assert config.redact_before_send is True
    assert config.allow_remote_endpoint is False
    assert config.timeout_seconds == 10


@pytest.mark.parametrize(
    "base_url",
    [
        "https://models.example.invalid:11434",
        "http://models.example.invalid:11434",
        "http://user:password@localhost:11434",
        "http://localhost:11434/api",
        "file:///tmp/model",
    ],
)
def test_model_config_rejects_non_loopback_or_unsafe_endpoints(project_root, base_url):
    data = _config(project_root)
    data["base_url"] = base_url
    with pytest.raises(ConfigError, match="loopback"):
        parse_local_model_config(data)


def test_model_config_rejects_unapproved_default_model(project_root):
    data = _config(project_root)
    data["default_model"] = "unapproved:latest"
    with pytest.raises(ConfigError, match="included in models"):
        parse_local_model_config(data)


def test_model_config_rejects_weakened_rules_and_unbounded_timeout(project_root):
    weakened = _config(project_root)
    weakened["rules"]["allow_remote_endpoint"] = True
    with pytest.raises(ConfigError, match="deny remote"):
        parse_local_model_config(weakened)

    unbounded = deepcopy(_config(project_root))
    unbounded["timeout_seconds"] = 31
    with pytest.raises(ConfigError, match="must not exceed"):
        parse_local_model_config(unbounded)


def test_direct_model_config_construction_cannot_bypass_loopback_boundary():
    with pytest.raises(ConfigError, match="loopback"):
        LocalModelConfig(
            base_url="https://models.example.invalid:11434",
            default_model="approved:latest",
            approved_models=("approved:latest",),
            timeout_seconds=10,
            structured_json=True,
            redact_before_send=True,
            allow_remote_endpoint=False,
        )


def test_direct_model_config_construction_cannot_weaken_rules():
    with pytest.raises(ConfigError, match="cannot weaken"):
        LocalModelConfig(
            base_url="http://localhost:11434",
            default_model="approved:latest",
            approved_models=("approved:latest",),
            timeout_seconds=10,
            structured_json=True,
            redact_before_send=False,
            allow_remote_endpoint=False,
        )
