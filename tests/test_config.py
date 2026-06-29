import pytest

from aotp.config import ConfigError, load_yaml, validate_scope_shape


def test_example_scope_is_structurally_valid(project_root):
    loaded = load_yaml(project_root / "config/scope.example.yaml")
    validate_scope_shape(loaded.data)


def test_missing_config_fails_closed(tmp_path):
    with pytest.raises(ConfigError):
        load_yaml(tmp_path / "missing.yaml")
