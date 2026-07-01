"""WSTG session management classification helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aotp.evidence_classifier import EvidenceClassification, classify_mapping, classify_text


class SessionManagementError(ValueError):
    """Raised when session material handling is unsafe."""


@dataclass(frozen=True)
class SessionObservation:
    cookie_names: tuple[str, ...]
    attributes: dict[str, dict[str, bool]]
    classification: EvidenceClassification
    vault_handle: str | None
    raw_values_included: bool = False

    def __post_init__(self) -> None:
        if self.raw_values_included:
            raise SessionManagementError("session observations cannot include raw cookie values")
        if self.classification is EvidenceClassification.SECRET and not self.vault_handle:
            raise SessionManagementError("secret session material requires a vault handle")

    def as_dict(self) -> dict[str, Any]:
        return {
            "cookie_names": list(self.cookie_names),
            "attributes": self.attributes,
            "classification": self.classification.value,
            "vault_handle": self.vault_handle,
            "raw_values_included": self.raw_values_included,
        }


def classify_session_text(value: str | bytes) -> EvidenceClassification:
    result = classify_text(value, context="session material")
    return result.classification


def build_session_observation(
    *,
    cookies: dict[str, dict[str, bool]],
    vault_handle: str | None = None,
) -> SessionObservation:
    if any("value" in attributes for attributes in cookies.values()):
        raise SessionManagementError("cookie values must be vaulted or memory-only, not normal evidence")
    classification = classify_mapping({"session_cookie_names": sorted(cookies)})
    return SessionObservation(
        cookie_names=tuple(sorted(cookies)),
        attributes={name: dict(attributes) for name, attributes in sorted(cookies.items())},
        classification=classification.classification,
        vault_handle=vault_handle,
    )
