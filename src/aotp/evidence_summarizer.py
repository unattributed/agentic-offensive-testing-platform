"""Classified summaries for returning bounded tool evidence to the agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from .agent_tools.http_metadata import ToolExecutionResult


EvidenceClassification = Literal["public", "restricted"]


@dataclass(frozen=True)
class EvidenceSummary:
    iteration: int
    objective_id: str
    tool_name: str
    classification: EvidenceClassification
    artifact_reference: str
    artifact_sha256: str
    request_count: int
    observations: dict[str, Any]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_tool_result(
    *,
    iteration: int,
    objective_id: str,
    result: ToolExecutionResult,
    artifact_reference: str,
    artifact_sha256: str,
) -> EvidenceSummary:
    observations: dict[str, Any]
    if result.tool_name == "http_metadata":
        payload = result.result
        observations = {
            "status": payload.get("status"),
            "headers": payload.get("headers", {}),
            "body_bytes_observed": payload.get("body_bytes_observed"),
            "body_sha256": payload.get("body_sha256"),
            "body_truncated": payload.get("body_truncated"),
        }
    elif result.tool_name == "well_known_text":
        observations = {
            "checks": [
                {
                    "url": item.get("url"),
                    "status": item.get("status"),
                    "content_type": item.get("headers", {}).get("content-type"),
                    "body_sha256": item.get("body_sha256"),
                    "body_truncated": item.get("body_truncated"),
                }
                for item in result.result.get("checks", [])
                if isinstance(item, dict)
            ]
        }
    elif result.tool_name == "tls_metadata":
        observations = {
            key: result.result.get(key)
            for key in (
                "tls_version",
                "cipher",
                "certificate_sha256",
                "subject",
                "issuer",
                "not_before",
                "not_after",
                "subject_alt_names",
            )
        }
    else:
        raise ValueError("unsupported Sprint 14 tool result")
    return EvidenceSummary(
        iteration=iteration,
        objective_id=objective_id,
        tool_name=result.tool_name,
        classification="public",
        artifact_reference=artifact_reference,
        artifact_sha256=artifact_sha256,
        request_count=result.request_count,
        observations=observations,
        limitations=(
            "Metadata-only observation does not by itself establish a vulnerability.",
            "No credential, state-changing action, payload injection, or exploitation was used.",
        ),
    )
