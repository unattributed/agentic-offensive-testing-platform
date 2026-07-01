"""Sensitive evidence classification for campaign artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class EvidenceClassification(str, Enum):
    PUBLIC = "public"
    RESTRICTED = "restricted"
    SECRET = "secret"
    POC_SENSITIVE = "poc_sensitive"
    RECIPIENT_ONLY = "recipient_only"
    DO_NOT_STORE = "do_not_store"


class EvidenceClassificationError(ValueError):
    """Raised when evidence classification or storage policy is invalid."""


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key_marker", re.compile(r"BEGIN\s+(?:RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE\s+KEY", re.I)),
    ("bearer_token", re.compile(r"authorization\s*:\s*bearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I)),
    ("cookie_header", re.compile(r"cookie\s*:\s*[^\s]+", re.I)),
    ("password_assignment", re.compile(r"\bpass(?:word)?\b\s*[:=]\s*[^\s]{6,}", re.I)),
    ("api_key_assignment", re.compile(r"\bapi[_-]?key\b\s*[:=]\s*[A-Za-z0-9._~+/=-]{8,}", re.I)),
    ("session_identifier", re.compile(r"\bsession[_-]?id\b[\"\']?\s*[:=]\s*[\"\']?[A-Za-z0-9._~+/=-]{8,}", re.I)),
    ("csrf_token", re.compile(r"\bcsrf[_-]?token\b[\"\']?\s*[:=]\s*[\"\']?[A-Za-z0-9._~+/=-]{8,}", re.I)),
)
_POC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("poc_material", re.compile(r"\b(?:proof[_ -]?of[_ -]?concept|poc|replay[_ -]?steps?)\b", re.I)),
    ("exploit_input", re.compile(r"\b(?:exploit[_ -]?input|validation[_ -]?payload)\b", re.I)),
)
_RECIPIENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("recipient_only_marker", re.compile(r"\brecipient[_ -]?only\b", re.I)),
    ("triager_private_marker", re.compile(r"\btriager[_ -]?private\b", re.I)),
)
_DO_NOT_STORE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("do_not_store_marker", re.compile(r"\bdo[_ -]?not[_ -]?store\b", re.I)),
    ("memory_only_marker", re.compile(r"\bmemory[_ -]?only\b", re.I)),
)

_STORAGE_ALLOWED = {
    EvidenceClassification.PUBLIC,
    EvidenceClassification.RESTRICTED,
    EvidenceClassification.SECRET,
    EvidenceClassification.POC_SENSITIVE,
    EvidenceClassification.RECIPIENT_ONLY,
}

_NORMAL_EVIDENCE_ALLOWED = {
    EvidenceClassification.PUBLIC,
    EvidenceClassification.RESTRICTED,
}


@dataclass(frozen=True)
class ClassificationResult:
    classification: EvidenceClassification
    reasons: tuple[str, ...]
    may_store: bool
    normal_evidence_allowed: bool
    vault_required: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "reasons": list(self.reasons),
            "may_store": self.may_store,
            "normal_evidence_allowed": self.normal_evidence_allowed,
            "vault_required": self.vault_required,
        }


def parse_classification(value: str | EvidenceClassification) -> EvidenceClassification:
    try:
        return value if isinstance(value, EvidenceClassification) else EvidenceClassification(value)
    except ValueError as exc:
        raise EvidenceClassificationError(f"unsupported evidence classification: {value}") from exc


def classify_text(value: str | bytes, *, context: str = "") -> ClassificationResult:
    """Classify a synthetic evidence value without exposing it to normal evidence."""

    text = value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)
    haystack = f"{context}\n{text}"
    matches: list[str] = []
    classification = EvidenceClassification.PUBLIC
    for name, pattern in _DO_NOT_STORE_PATTERNS:
        if pattern.search(haystack):
            matches.append(name)
            classification = EvidenceClassification.DO_NOT_STORE
            break
    if classification is not EvidenceClassification.DO_NOT_STORE:
        for name, pattern in _SECRET_PATTERNS:
            if pattern.search(haystack):
                matches.append(name)
                classification = EvidenceClassification.SECRET
        for name, pattern in _POC_PATTERNS:
            if pattern.search(haystack):
                matches.append(name)
                if classification is EvidenceClassification.PUBLIC:
                    classification = EvidenceClassification.POC_SENSITIVE
        for name, pattern in _RECIPIENT_PATTERNS:
            if pattern.search(haystack):
                matches.append(name)
                if classification in {EvidenceClassification.PUBLIC, EvidenceClassification.RESTRICTED}:
                    classification = EvidenceClassification.RECIPIENT_ONLY
    if not matches and context.strip():
        classification = EvidenceClassification.RESTRICTED
        matches.append("contextual_campaign_evidence")
    return policy_for_classification(classification, reasons=tuple(matches or ("no_sensitive_marker",)))


def classify_mapping(value: dict[str, Any]) -> ClassificationResult:
    encoded = repr(value)
    return classify_text(encoded, context="mapping")


def policy_for_classification(
    classification: str | EvidenceClassification,
    *,
    reasons: tuple[str, ...] = (),
) -> ClassificationResult:
    parsed = parse_classification(classification)
    return ClassificationResult(
        classification=parsed,
        reasons=reasons,
        may_store=parsed in _STORAGE_ALLOWED,
        normal_evidence_allowed=parsed in _NORMAL_EVIDENCE_ALLOWED,
        vault_required=parsed not in _NORMAL_EVIDENCE_ALLOWED,
    )


def assert_may_store(classification: str | EvidenceClassification) -> EvidenceClassification:
    parsed = parse_classification(classification)
    if parsed is EvidenceClassification.DO_NOT_STORE:
        raise EvidenceClassificationError("do_not_store material cannot be persisted")
    return parsed


def assert_normal_evidence_safe(value: str | bytes, *, context: str = "") -> None:
    result = classify_text(value, context=context)
    if not result.normal_evidence_allowed:
        raise EvidenceClassificationError("raw material is not allowed in normal evidence")
