"""Bounded local Ollama structured JSON adapter."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from ..model_config import LocalModelConfig
from ..redaction import assert_redacted, assert_value_redacted, sanitize_for_model

MAX_RESPONSE_BYTES = 1_048_576
DEFAULT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
}


class OllamaAdapterError(RuntimeError):
    """Base class for bounded local model failures."""


class OllamaUnavailableError(OllamaAdapterError):
    """Raised when the configured local service cannot be reached in time."""


class OllamaResponseError(OllamaAdapterError):
    """Raised when the local service returns malformed or out-of-schema data."""


class OllamaPromptError(OllamaAdapterError):
    """Raised when safe prompt construction cannot be completed."""


def default_local_model_config() -> LocalModelConfig:
    return LocalModelConfig(
        base_url="http://localhost:11434",
        default_model="qwen3:8b",
        approved_models=("qwen3:8b",),
        timeout_seconds=10,
        structured_json=True,
        redact_before_send=True,
        allow_remote_endpoint=False,
    )


def _validate_schema_value(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise OllamaResponseError(f"{path} must be an object")
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            raise OllamaResponseError("response schema is invalid")
        missing = sorted(set(required) - set(value))
        if missing:
            raise OllamaResponseError(f"{path} is missing required fields: {', '.join(missing)}")
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                raise OllamaResponseError(
                    f"{path} contains unknown fields: {', '.join(unknown)}"
                )
        for key, item in value.items():
            child_schema = properties.get(key)
            if isinstance(child_schema, dict):
                _validate_schema_value(item, child_schema, f"{path}.{key}")
    elif expected == "array":
        if not isinstance(value, list):
            raise OllamaResponseError(f"{path} must be an array")
        item_schema = schema.get("items")
        if not isinstance(item_schema, dict):
            raise OllamaResponseError("response schema is invalid")
        for index, item in enumerate(value):
            _validate_schema_value(item, item_schema, f"{path}[{index}]")
    elif expected == "string":
        if not isinstance(value, str):
            raise OllamaResponseError(f"{path} must be a string")
    elif expected == "boolean":
        if not isinstance(value, bool):
            raise OllamaResponseError(f"{path} must be a boolean")
    elif expected == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise OllamaResponseError(f"{path} must be an integer")
    elif expected == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise OllamaResponseError(f"{path} must be a number")
    else:
        raise OllamaResponseError(f"{path} uses an unsupported response schema type")
    if "enum" in schema and value not in schema["enum"]:
        raise OllamaResponseError(f"{path} contains an unsupported value")


@dataclass(frozen=True)
class OllamaAdapter:
    config: LocalModelConfig = field(default_factory=default_local_model_config)
    model: str | None = None
    opener: Callable[..., Any] = field(
        default=urllib.request.urlopen,
        repr=False,
        compare=False,
    )

    supports = (
        "structured_planning",
        "evidence_summarization",
        "classification",
        "draft_language",
    )
    requires = ("loopback_endpoint", "approved_model", "redacted_input", "response_schema")
    denies = ("scope_authorization", "policy_override", "raw_secrets", "remote_endpoint")

    def __post_init__(self) -> None:
        selected = self.model or self.config.default_model
        if not self.config.approves(selected):
            raise ValueError("model is not approved by local model configuration")
        object.__setattr__(self, "model", selected)

    def build_prompt(
        self,
        task: str,
        payload: dict[str, Any],
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        schema = response_schema or DEFAULT_RESPONSE_SCHEMA
        cleaned = sanitize_for_model({"task": task, "payload": payload})
        try:
            encoded = json.dumps(cleaned, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise OllamaPromptError("model prompt must be JSON-serializable") from exc
        assert_redacted(encoded)
        assert_value_redacted(cleaned)
        return {
            "model": self.model,
            "format": schema,
            "stream": False,
            "options": {"temperature": 0},
            "prompt": encoded,
        }

    def generate(
        self,
        task: str,
        payload: dict[str, Any],
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        schema = response_schema or DEFAULT_RESPONSE_SCHEMA
        body = json.dumps(
            self.build_prompt(task, payload, schema),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        request = urllib.request.Request(
            self.config.base_url.rstrip("/") + "/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            raise OllamaUnavailableError(
                "local Ollama service is unavailable within the configured timeout"
            ) from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise OllamaResponseError("local Ollama response exceeds the size limit")
        try:
            envelope = json.loads(raw)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OllamaResponseError("local Ollama service returned invalid JSON") from exc
        if (
            not isinstance(envelope, dict)
            or envelope.get("done") is not True
            or not isinstance(envelope.get("response"), str)
        ):
            raise OllamaResponseError("local Ollama response envelope is incomplete")
        try:
            result = json.loads(envelope["response"])
        except json.JSONDecodeError as exc:
            raise OllamaResponseError("local Ollama structured response is invalid JSON") from exc
        _validate_schema_value(result, schema)
        try:
            assert_redacted(json.dumps(result, sort_keys=True))
            assert_value_redacted(result)
        except ValueError as exc:
            raise OllamaResponseError("local Ollama response failed redaction checks") from exc
        return result
