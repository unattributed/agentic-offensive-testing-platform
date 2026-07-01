"""Strict structured proposals emitted by the Sprint 14 Deep Agent."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


ToolName = Literal["http_metadata", "tls_metadata", "well_known_text"]


class ModelProposalError(ValueError):
    """Raised when model output does not satisfy the proposal contract."""


class HttpMetadataArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    url: str = Field(min_length=1, max_length=2048)


class TlsMetadataArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    host: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535)
    server_name: str = Field(min_length=1, max_length=253)


class WellKnownArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    base_url: str = Field(min_length=1, max_length=2048)


ProposalArguments = HttpMetadataArguments | TlsMetadataArguments | WellKnownArguments


class ModelProposal(BaseModel):
    """One model-proposed objective and native tool invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    objective_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    tool_name: ToolName
    target_alias: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
    )
    arguments: ProposalArguments
    rationale: str = Field(min_length=1, max_length=1000)

    @property
    def arguments_dict(self) -> dict[str, Any]:
        if isinstance(self.arguments, BaseModel):
            return self.arguments.model_dump()
        if isinstance(self.arguments, dict):
            return dict(self.arguments)
        raise ModelProposalError("model proposal arguments are not structured")


def proposal_json_schema() -> dict[str, Any]:
    """Return the strict schema supplied to the local model."""

    return ModelProposal.model_json_schema()


def parse_model_proposal(value: ModelProposal | dict[str, Any] | str) -> ModelProposal:
    """Parse model output and reject non-object, unknown, or weakly typed fields."""

    try:
        if isinstance(value, ModelProposal):
            return value
        if isinstance(value, str):
            decoded = json.loads(value)
            if not isinstance(decoded, dict):
                raise ModelProposalError("model proposal JSON must be an object")
            value = decoded
        if not isinstance(value, dict):
            raise ModelProposalError("model proposal must be a mapping or JSON object")
        return ModelProposal.model_validate(value)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ModelProposalError("model proposal is malformed or out of schema") from exc
