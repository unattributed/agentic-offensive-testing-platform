"""Redacted session evidence routing for authenticated OSMAP checks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .csrf import SessionMaterialKind, material_default_classification
from .vault_handles import parse_vault_handle


class SessionEvidenceError(ValueError):
    """Raised when session material would leak into normal evidence."""


class SessionStorageRoute(str, Enum):
    VAULTED = "vaulted"
    MEMORY_ONLY = "memory_only"
    DO_NOT_STORE = "do_not_store"
    PUBLIC_METADATA_ONLY = "public_metadata_only"


@dataclass(frozen=True)
class SessionEvidenceRecord:
    material_kind: SessionMaterialKind
    alias: str
    route: SessionStorageRoute
    classification: str
    source: str
    value_sha256: str | None = None
    vault_handle: str | None = None
    redacted: bool = True

    def __post_init__(self) -> None:
        if not self.alias or any(character in self.alias for character in "/\\ \t\n\r"):
            raise SessionEvidenceError("session evidence alias is unsafe")
        if not self.source or any(character in self.source for character in "\n\r"):
            raise SessionEvidenceError("session evidence source is unsafe")
        if self.classification not in {"restricted", "secret", "poc_sensitive", "recipient_only"}:
            raise SessionEvidenceError("unsupported session evidence classification")
        if self.route is SessionStorageRoute.VAULTED:
            if not self.vault_handle:
                raise SessionEvidenceError("vaulted material requires a vault handle")
            parse_vault_handle(self.vault_handle)
        if self.route in {SessionStorageRoute.MEMORY_ONLY, SessionStorageRoute.DO_NOT_STORE}:
            if self.value_sha256 is not None or self.vault_handle is not None:
                raise SessionEvidenceError("memory-only and do-not-store material cannot persist handles or hashes")
        if not self.redacted:
            raise SessionEvidenceError("session evidence records must be redacted")

    def as_dict(self) -> dict[str, object]:
        payload = {
            "material_kind": self.material_kind.value,
            "alias": self.alias,
            "route": self.route.value,
            "classification": self.classification,
            "source": self.source,
            "value_sha256": self.value_sha256,
            "vault_handle": self.vault_handle,
            "redacted": self.redacted,
        }
        _assert_metadata_contains_no_raw_session_value(payload)
        return payload


def build_session_evidence_record(
    *,
    material_kind: SessionMaterialKind | str,
    alias: str,
    raw_value: str | bytes | None,
    storage_route: SessionStorageRoute | str,
    source: str,
    vault_handle: str | None = None,
    classification: str | None = None,
) -> SessionEvidenceRecord:
    """Build a redacted public metadata record for session material."""

    parsed_kind = SessionMaterialKind(material_kind)
    parsed_route = SessionStorageRoute(storage_route)
    chosen_classification = classification or material_default_classification(parsed_kind)
    digest = None
    if parsed_route is SessionStorageRoute.PUBLIC_METADATA_ONLY:
        if raw_value is not None:
            data = raw_value.encode("utf-8") if isinstance(raw_value, str) else bytes(raw_value)
            digest = hashlib.sha256(data).hexdigest()
    elif parsed_route is SessionStorageRoute.VAULTED:
        if raw_value is not None:
            data = raw_value.encode("utf-8") if isinstance(raw_value, str) else bytes(raw_value)
            digest = hashlib.sha256(data).hexdigest()
    elif parsed_route in {SessionStorageRoute.MEMORY_ONLY, SessionStorageRoute.DO_NOT_STORE}:
        digest = None
        vault_handle = None
    return SessionEvidenceRecord(
        material_kind=parsed_kind,
        alias=alias,
        route=parsed_route,
        classification=chosen_classification,
        source=source,
        value_sha256=digest,
        vault_handle=vault_handle,
    )


def assert_public_session_record_safe(record: SessionEvidenceRecord | dict[str, Any]) -> None:
    payload = record.as_dict() if isinstance(record, SessionEvidenceRecord) else dict(record)
    _assert_metadata_contains_no_raw_session_value(payload)


def _assert_metadata_contains_no_raw_session_value(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    disallowed = (
        "cookie" + ": ",
        "authorization" + ": bearer",
        "password=",
        "csrf_token=",
        "session" + "_id=",
    )
    if any(marker in encoded.lower() for marker in disallowed):
        raise SessionEvidenceError("session evidence metadata contains raw session material")
    if payload.get("redacted") is not True:
        raise SessionEvidenceError("session evidence metadata must be redacted")
