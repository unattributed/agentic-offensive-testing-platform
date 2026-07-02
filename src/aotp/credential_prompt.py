"""Interactive credential collection helpers for authenticated campaigns.

The helpers in this module intentionally avoid command-line arguments for
provisioned credentials. Secrets are held only in memory, have redacted string
representations, and can be explicitly cleared by the caller after an
operator-approved authenticated campaign step finishes.
"""

from __future__ import annotations

import getpass
import hashlib
import re
from dataclasses import dataclass
from typing import Callable


class CredentialPromptError(ValueError):
    """Raised when credential prompt input is unsafe or incomplete."""


_ALIAS_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class SecretInput:
    """A small in-memory secret wrapper with redacted public representation."""

    __slots__ = ("label", "_value", "_cleared")

    def __init__(self, value: str, *, label: str) -> None:
        if not isinstance(value, str) or not value:
            raise CredentialPromptError(f"{label} is required")
        if any(character in value for character in "\x00\n\r"):
            raise CredentialPromptError(f"{label} contains unsupported control characters")
        self.label = _safe_label(label)
        self._value = value
        self._cleared = False

    def __repr__(self) -> str:
        return f"SecretInput(label={self.label!r}, redacted=True, cleared={self._cleared})"

    def __str__(self) -> str:
        return "<redacted-secret>"

    @property
    def value(self) -> str:
        if self._cleared:
            raise CredentialPromptError(f"{self.label} has been cleared")
        return self._value

    @property
    def is_cleared(self) -> bool:
        return self._cleared

    def clear(self) -> None:
        self._value = ""
        self._cleared = True

    def sha256(self) -> str:
        return hashlib.sha256(self.value.encode("utf-8")).hexdigest()

    def as_public_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "present": not self._cleared,
            "redacted": True,
            "cleared": self._cleared,
        }


@dataclass
class CredentialBundle:
    """Provisioned authenticated-account material returned from prompts."""

    operator_alias: str
    account_alias: str
    username: str
    password: SecretInput
    totp: SecretInput | None = None

    def __post_init__(self) -> None:
        self.operator_alias = _safe_alias(self.operator_alias, "operator_alias")
        self.account_alias = _safe_alias(self.account_alias, "account_alias")
        if not isinstance(self.username, str) or not self.username.strip():
            raise CredentialPromptError("username is required")
        if any(character in self.username for character in "\x00\n\r"):
            raise CredentialPromptError("username contains unsupported control characters")

    def __repr__(self) -> str:
        username_digest = hashlib.sha256(self.username.encode("utf-8")).hexdigest()
        return (
            "CredentialBundle("
            f"operator_alias={self.operator_alias!r}, "
            f"account_alias={self.account_alias!r}, "
            f"username_sha256={username_digest!r}, "
            "password=<redacted>, totp=<redacted>)"
        )

    def clear(self) -> None:
        self.password.clear()
        if self.totp is not None:
            self.totp.clear()

    def as_public_dict(self) -> dict[str, object]:
        return {
            "operator_alias": self.operator_alias,
            "account_alias": self.account_alias,
            "username_sha256": hashlib.sha256(self.username.encode("utf-8")).hexdigest(),
            "password": self.password.as_public_dict(),
            "totp": self.totp.as_public_dict() if self.totp else None,
            "redacted": True,
        }


def collect_credentials(
    *,
    prompt: Callable[[str], str] = input,
    secret_prompt: Callable[[str], str] = getpass.getpass,
    require_totp: bool = False,
    operator_alias: str | None = None,
    account_alias: str | None = None,
) -> CredentialBundle:
    """Collect authenticated campaign credentials interactively."""

    resolved_operator = operator_alias or prompt("Operator alias: ").strip()
    resolved_account = account_alias or prompt("Account alias: ").strip()
    username = prompt("Username: ").strip()
    password = SecretInput(secret_prompt("Password: "), label="password")
    totp_value = secret_prompt("TOTP code: ") if require_totp else ""
    totp = SecretInput(totp_value, label="totp") if require_totp else None
    return CredentialBundle(
        operator_alias=resolved_operator,
        account_alias=resolved_account,
        username=username,
        password=password,
        totp=totp,
    )


def assert_no_secret_arguments(arguments: list[str] | tuple[str, ...]) -> None:
    """Deny credential-like material supplied through command arguments."""

    joined = "\n".join(arguments)
    lowered = joined.lower()
    secret_markers = (
        "password=",
        "--password",
        "totp=",
        "--totp",
        "cookie" + ":",
        "authorization:",
        "session" + "_id=",
        "csrf_token=",
    )
    if any(marker in lowered for marker in secret_markers):
        raise CredentialPromptError("secrets must not be supplied through command arguments")


def _safe_alias(value: str, field: str) -> str:
    if not isinstance(value, str) or _ALIAS_RE.fullmatch(value) is None:
        raise CredentialPromptError(f"{field} must be a safe lowercase alias")
    return value


def _safe_label(value: str) -> str:
    if not isinstance(value, str) or not value or any(character in value for character in "\n\r\t"):
        raise CredentialPromptError("secret label is unsafe")
    return value
