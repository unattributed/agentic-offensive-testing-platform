import pytest

from aotp.adapters.ollama_adapter import OllamaAdapter
from aotp.redaction import (
    assert_redacted,
    assert_value_redacted,
    findings,
    sanitize_for_model,
    sanitize_with_report,
    scan_value,
)


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


def test_structured_redaction_reports_path_without_secret_value():
    secret = "super-secret-value"
    value = {"request": {"headers": {"authorization": secret}}}
    matches = scan_value(value)
    assert matches[0].path == "$.request.headers.authorization"
    assert matches[0].kind == "sensitive_field"
    assert secret not in repr(matches)
    with pytest.raises(ValueError, match=r"\$\.request\.headers\.authorization"):
        assert_value_redacted(value)


def test_structured_sanitizer_redacts_sensitive_keys_and_nested_patterns():
    value = {
        "password": "not-for-output",
        "nested": ["person" + "@" + "example.invalid"],
        "authorization_reference": "safe-reference",
    }
    cleaned, report = sanitize_with_report(value)
    assert cleaned["password"] == "[REDACTED:sensitive_field]"
    assert cleaned["nested"] == ["[REDACTED]"]
    assert cleaned["authorization_reference"] == "safe-reference"
    assert {finding.kind for finding in report} >= {"sensitive_field", "email_address"}


@pytest.mark.parametrize(
    "field",
    [
        "access_token",
        "client_secret",
        "cookie_value",
        "credentials",
        "private_key_material",
        "raw_cookie",
        "raw_token",
        "refresh_token",
        "session_cookie",
        "token_value",
    ],
)
def test_extended_secret_fields_are_redacted_recursively(field):
    value = {"outer": [{"inner": {field: "not-for-model"}}]}
    cleaned, report = sanitize_with_report(value)
    assert cleaned["outer"][0]["inner"][field] == "[REDACTED:sensitive_field]"
    assert {finding.kind for finding in report} == {"sensitive_field"}
    assert "not-for-model" not in repr(cleaned)


def test_secret_pattern_in_mapping_key_is_redacted_without_path_leak():
    secret_key = "person" + "@" + "example.invalid"
    cleaned, report = sanitize_with_report({secret_key: "metadata"})
    assert cleaned == {"[REDACTED:key:0]": "metadata"}
    assert secret_key not in repr(report)
    assert report[0].path == "$.[redacted-key]"


def test_model_prompt_recursively_strips_all_supported_secret_classes():
    secrets = {
        "authorization": "Bearer " + "abc.def.ghi123",
        "nested": [
            {"cookie_value": "cookie-secret"},
            {"private_key_material": "private-key-secret"},
            "person" + "@" + "example.invalid",
        ],
    }
    prompt = OllamaAdapter().build_prompt("summarize", secrets)
    encoded = prompt["prompt"]
    assert all(
        secret not in encoded
        for secret in (
            "abc.def.ghi123",
            "cookie-secret",
            "private-key-secret",
            "person" + "@" + "example.invalid",
        )
    )
    assert findings(encoded) == []


def test_github_token_and_jwt_are_blocked():
    github_token = "ghp_" + "a" * 30
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature"
    assert {finding.kind for finding in scan_value([github_token, jwt])} == {
        "github_token",
        "jwt",
    }

# SPRINT4_EXTERNAL_REFERENCE_REDACTION_TESTS
import pytest
from aotp.external_evidence import validate_external_evidence_reference


def test_external_reference_requires_redaction_status(tmp_path):
    reference = {
        "alias": "storage-state",
        "relative_path": "browser/storage-state.redacted.json",
        "sha256": "b" * 64,
        "provenance": "placeholder contract",
        "source_project_or_adapter_contract": "playwright",
        "redaction_status": "unredacted",
    }
    with pytest.raises(ValueError):
        validate_external_evidence_reference(reference, tmp_path)
