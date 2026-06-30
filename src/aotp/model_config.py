"""Fail-closed configuration for local structured model assistance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .config import (
    ConfigError,
    load_yaml,
    require_bool,
    require_mapping,
    require_positive_int,
    require_text,
    require_text_list,
)

LOCAL_MODEL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
MAX_MODEL_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class LocalModelConfig:
    base_url: str
    default_model: str
    approved_models: tuple[str, ...]
    timeout_seconds: int
    structured_json: bool
    redact_before_send: bool
    allow_remote_endpoint: bool

    def approves(self, model: str) -> bool:
        return model in self.approved_models


def _reject_unknown(mapping: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ConfigError(f"{field} contains unknown fields: {', '.join(unknown)}")


def _validate_local_url(value: str) -> str:
    parsed = urlsplit(value)
    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise ConfigError("base_url port is invalid") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname not in LOCAL_MODEL_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed_port is None
    ):
        raise ConfigError("base_url must be an unauthenticated loopback HTTP endpoint with a port")
    return value.rstrip("/")


def parse_local_model_config(data: dict[str, Any]) -> LocalModelConfig:
    _reject_unknown(
        data,
        {"schema_version", "base_url", "default_model", "models", "timeout_seconds", "rules"},
        "model configuration",
    )
    if require_text(data.get("schema_version"), "schema_version") != "1.0":
        raise ConfigError("unsupported model configuration schema_version")
    base_url = _validate_local_url(require_text(data.get("base_url"), "base_url"))
    default_model = require_text(data.get("default_model"), "default_model")
    approved_models = require_text_list(data.get("models"), "models", allow_empty=False)
    if len(approved_models) != len(set(approved_models)):
        raise ConfigError("models must not contain duplicates")
    if default_model not in approved_models:
        raise ConfigError("default_model must be included in models")
    timeout_seconds = require_positive_int(data.get("timeout_seconds"), "timeout_seconds")
    if timeout_seconds > MAX_MODEL_TIMEOUT_SECONDS:
        raise ConfigError(
            f"timeout_seconds must not exceed {MAX_MODEL_TIMEOUT_SECONDS}"
        )
    rules = require_mapping(data.get("rules"), "rules")
    _reject_unknown(
        rules,
        {"structured_json", "redact_before_send", "allow_remote_endpoint"},
        "rules",
    )
    structured_json = require_bool(rules.get("structured_json"), "rules.structured_json")
    redact_before_send = require_bool(
        rules.get("redact_before_send"), "rules.redact_before_send"
    )
    allow_remote_endpoint = require_bool(
        rules.get("allow_remote_endpoint"), "rules.allow_remote_endpoint"
    )
    if not structured_json or not redact_before_send or allow_remote_endpoint:
        raise ConfigError(
            "model rules must require structured JSON and redaction and deny remote endpoints"
        )
    return LocalModelConfig(
        base_url=base_url,
        default_model=default_model,
        approved_models=tuple(approved_models),
        timeout_seconds=timeout_seconds,
        structured_json=structured_json,
        redact_before_send=redact_before_send,
        allow_remote_endpoint=allow_remote_endpoint,
    )


def load_local_model_config(path: str | Path) -> LocalModelConfig:
    return parse_local_model_config(load_yaml(path).data)
