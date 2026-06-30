from __future__ import annotations

import json
from dataclasses import replace

import pytest

from aotp.adapters.ollama_adapter import (
    OllamaAdapter,
    OllamaResponseError,
    OllamaUnavailableError,
)
from aotp.model_config import load_local_model_config

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit: int) -> bytes:
        return self.body[:limit]


def _response(value) -> bytes:
    return json.dumps({"done": True, "response": json.dumps(value)}).encode()


def test_adapter_posts_bounded_structured_request(project_root):
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse(_response({"summary": "metadata only"}))

    adapter = OllamaAdapter(
        config=load_local_model_config(project_root / "config/models.example.yaml"),
        opener=opener,
    )
    result = adapter.generate("summarize", {"evidence": "safe"}, SUMMARY_SCHEMA)
    assert result == {"summary": "metadata only"}
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["timeout"] == 10
    assert captured["body"]["format"] == SUMMARY_SCHEMA
    assert captured["body"]["stream"] is False
    assert captured["body"]["options"] == {"temperature": 0}


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"not-json", "invalid JSON"),
        (json.dumps({"done": False, "response": "{}"}).encode(), "incomplete"),
        (json.dumps({"done": True, "response": "not-json"}).encode(), "structured response"),
        (_response({}), "missing required fields"),
        (_response({"summary": "safe", "authorization": True}), "unknown fields"),
    ],
)
def test_invalid_or_out_of_schema_responses_fail_gracefully(body, message):
    adapter = OllamaAdapter(opener=lambda *_args, **_kwargs: FakeResponse(body))
    with pytest.raises(OllamaResponseError, match=message):
        adapter.generate("summarize", {}, SUMMARY_SCHEMA)


def test_unavailable_service_has_bounded_error():
    def unavailable(*_args, **_kwargs):
        raise TimeoutError("local timeout detail")

    adapter = OllamaAdapter(opener=unavailable)
    with pytest.raises(OllamaUnavailableError, match="configured timeout"):
        adapter.generate("summarize", {}, SUMMARY_SCHEMA)


def test_unapproved_model_is_rejected(project_root):
    config = load_local_model_config(project_root / "config/models.example.yaml")
    restricted = replace(config, approved_models=("qwen3:8b",))
    with pytest.raises(ValueError, match="not approved"):
        OllamaAdapter(config=restricted, model="unapproved:latest")
