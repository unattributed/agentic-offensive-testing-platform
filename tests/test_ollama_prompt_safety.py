from __future__ import annotations

import json

import pytest

from aotp.adapters.ollama_adapter import (
    MAX_PROMPT_BYTES,
    OllamaAdapter,
    OllamaPromptError,
    OllamaResponseError,
)

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}


class FakeResponse:
    def __init__(self, result):
        self.body = json.dumps(
            {"done": True, "response": json.dumps(result)}
        ).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit):
        return self.body[:limit]


def test_no_secret_class_reaches_serialized_request_body():
    captured = {}
    secret_values = [
        "Bearer " + "abc.def.ghi123",
        "Cookie" + ": sid=abc123456789",
        "session_" + "id=abc123456789",
        "-----BEGIN " + "PRIVATE KEY-----",
        "person" + "@" + "example.invalid",
        "api_" + "key=abcdefghijklmnop",
        "AKIA" + "ABCDEFGHIJKLMNOP",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
    ]
    payload = {
        "authorization": secret_values[0],
        "nested": (
            {"raw_cookie": secret_values[1]},
            [{"private_key_material": secret_values[3]}],
            secret_values[2:],
        ),
    }

    def opener(request, timeout):
        captured["body"] = request.data.decode()
        captured["timeout"] = timeout
        return FakeResponse({"summary": "safe metadata"})

    result = OllamaAdapter(opener=opener).generate(
        "Summarize metadata.",
        payload,
        SUMMARY_SCHEMA,
    )
    assert result == {"summary": "safe metadata"}
    assert captured["timeout"] == 10
    assert all(secret not in captured["body"] for secret in secret_values)


@pytest.mark.parametrize(
    "payload",
    [
        {"unsupported": object()},
        {"unsupported": {1, 2}},
        {"non_finite": float("nan")},
    ],
)
def test_prompt_construction_fails_before_transport_for_unsafe_values(payload):
    called = False

    def opener(*_args, **_kwargs):
        nonlocal called
        called = True
        return FakeResponse({"summary": "should not run"})

    with pytest.raises(OllamaPromptError):
        OllamaAdapter(opener=opener).generate("Summarize.", payload, SUMMARY_SCHEMA)
    assert called is False


def test_oversized_prompt_fails_before_transport():
    called = False

    def opener(*_args, **_kwargs):
        nonlocal called
        called = True
        return FakeResponse({"summary": "should not run"})

    with pytest.raises(OllamaPromptError, match="size limit"):
        OllamaAdapter(opener=opener).generate(
            "Summarize.",
            {"summary": "a" * (MAX_PROMPT_BYTES + 1)},
            SUMMARY_SCHEMA,
        )
    assert called is False


@pytest.mark.parametrize(
    "summary",
    [
        "Bearer " + "abc.def.ghi123",
        "Cookie" + ": sid=abc123456789",
        "person" + "@" + "example.invalid",
        "-----BEGIN " + "PRIVATE KEY-----",
    ],
)
def test_secret_bearing_model_response_fails_closed(summary):
    adapter = OllamaAdapter(
        opener=lambda *_args, **_kwargs: FakeResponse({"summary": summary})
    )
    with pytest.raises(OllamaResponseError, match="redaction checks"):
        adapter.generate("Summarize.", {}, SUMMARY_SCHEMA)


def test_non_finite_structured_response_is_rejected():
    class NonFiniteResponse(FakeResponse):
        def __init__(self):
            self.body = b'{"done":true,"response":"{\\"summary\\":NaN}"}'

    adapter = OllamaAdapter(opener=lambda *_args, **_kwargs: NonFiniteResponse())
    with pytest.raises(OllamaResponseError, match="structured response"):
        adapter.generate("Summarize.", {}, SUMMARY_SCHEMA)
