import pytest

from aotp.adapters.ollama_adapter import OllamaAdapter
from aotp.redaction import assert_redacted, findings, sanitize_for_model


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Authorization: " + "Bearer " + "abc.def.ghi123", "bearer_token"),
        ("Cookie" + ": sid=abc123456789", "cookie"),
        ("session_" + "id=abc123456789", "session_id"),
        ("-----BEGIN " + "PRIVATE KEY-----", "private_key"),
        ("person" + "@" + "example.invalid", "email_address"),
        ("api_" + "key=abcdefghijklmnop", "api_key"),
        ("AKIA" + "ABCDEFGHIJKLMNOP", "aws_access_key"),
    ],
)
def test_obvious_secrets_are_blocked(value, expected):
    assert expected in findings(value)
    with pytest.raises(ValueError):
        assert_redacted(value)


def test_model_prompt_is_sanitized():
    secret = "Bearer " + "abc.def.ghi123"
    payload = OllamaAdapter().build_prompt("summarize", {"authorization": secret})
    assert secret not in payload["prompt"]
    assert sanitize_for_model(secret) == "[REDACTED]"
