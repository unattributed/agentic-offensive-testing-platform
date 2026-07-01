"""Opaque handles for sensitive vault records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_HANDLE_ID = re.compile(r"^[a-f0-9]{32}$")
_SAFE_COMPONENT = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class VaultHandleError(ValueError):
    """Raised when a vault handle is malformed."""


@dataclass(frozen=True)
class VaultHandle:
    campaign_id: str
    handle_id: str
    classification: str
    artifact_kind: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("campaign_id", self.campaign_id),
            ("classification", self.classification),
            ("artifact_kind", self.artifact_kind),
        ):
            if _SAFE_COMPONENT.fullmatch(value) is None:
                raise VaultHandleError(f"{field_name} is not a safe handle component")
        if _HANDLE_ID.fullmatch(self.handle_id) is None:
            raise VaultHandleError("handle_id must be a 32 character lowercase hex value")

    @property
    def uri(self) -> str:
        return f"vault://{self.campaign_id}/{self.classification}/{self.artifact_kind}/{self.handle_id}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "campaign_id": self.campaign_id,
            "handle_id": self.handle_id,
            "classification": self.classification,
            "artifact_kind": self.artifact_kind,
        }


def parse_vault_handle(uri: str) -> VaultHandle:
    prefix = "vault://"
    if not isinstance(uri, str) or not uri.startswith(prefix):
        raise VaultHandleError("vault handle must use the vault:// scheme")
    parts = uri[len(prefix):].split("/")
    if len(parts) != 4:
        raise VaultHandleError("vault handle has an invalid component count")
    return VaultHandle(
        campaign_id=parts[0],
        classification=parts[1],
        artifact_kind=parts[2],
        handle_id=parts[3],
    )


def assert_handle_only(value: str) -> None:
    parse_vault_handle(value)
