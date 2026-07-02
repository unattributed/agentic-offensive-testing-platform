import json

import pytest

from aotp.credential_prompt import (
    CredentialPromptError,
    SecretInput,
    assert_no_secret_arguments,
    collect_credentials,
)


def test_secret_input_redacts_repr_string_and_public_dict():
    secret = SecretInput("correct horse battery staple", label="password")

    rendered = repr(secret) + str(secret) + json.dumps(secret.as_public_dict())

    assert "correct horse" not in rendered
    assert "redacted" in rendered


def test_secret_input_can_be_cleared():
    secret = SecretInput("temporary-secret", label="password")
    assert secret.value == "temporary-secret"

    secret.clear()

    assert secret.is_cleared is True
    with pytest.raises(CredentialPromptError):
        _ = secret.value


def test_collect_credentials_uses_secret_prompt_for_password_and_totp():
    prompts = iter(["agent-one", "account-one", "operator@example.test"])
    secrets = iter(["test-password-value", "123456"])

    bundle = collect_credentials(
        prompt=lambda _: next(prompts),
        secret_prompt=lambda _: next(secrets),
        require_totp=True,
    )

    rendered = repr(bundle) + json.dumps(bundle.as_public_dict(), sort_keys=True)
    assert bundle.operator_alias == "agent-one"
    assert bundle.account_alias == "account-one"
    assert bundle.password.value == "test-password-value"
    assert bundle.totp is not None
    assert bundle.totp.value == "123456"
    assert "test-password-value" not in rendered
    assert "123456" not in rendered
    assert "operator@example.test" not in rendered


def test_assert_no_secret_arguments_fails_closed():
    with pytest.raises(CredentialPromptError):
        assert_no_secret_arguments(["--password", "do-not-pass-this"])

    assert_no_secret_arguments(["--account-alias", "account-one"])
