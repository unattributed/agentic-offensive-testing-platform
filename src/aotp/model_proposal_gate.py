"""Fail-closed policy gate for model-proposed Sprint 14 objectives."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
from urllib.parse import urlsplit

from .model_proposals import ModelProposal


class ProposalPolicyError(ValueError):
    """Raised when a campaign policy is unsafe or incomplete."""


@dataclass(frozen=True)
class CampaignObjective:
    objective_id: str
    tool_name: str
    arguments: dict[str, Any]

    def as_model_context(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
        }


@dataclass(frozen=True)
class AgentCampaignPolicy:
    campaign_id: str
    program_alias: str
    target_alias: str
    base_url: str
    authorization_reference: str
    operator_approved: bool
    objectives: tuple[CampaignObjective, ...]
    max_iterations: int = 3
    max_requests: int = 4

    def __post_init__(self) -> None:
        for field, value in (
            ("campaign_id", self.campaign_id),
            ("program_alias", self.program_alias),
            ("target_alias", self.target_alias),
        ):
            if (
                not isinstance(value, str)
                or re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", value) is None
            ):
                raise ProposalPolicyError(
                    f"{field} must be a safe lowercase campaign identifier"
                )
        parsed = urlsplit(self.base_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ProposalPolicyError(
                "Sprint 14 base_url must be an origin-only HTTPS URL without credentials"
            )
        if not self.operator_approved:
            raise ProposalPolicyError("Sprint 14 live campaign requires operator approval")
        if (
            not self.authorization_reference.strip()
            or "placeholder" in self.authorization_reference.lower()
            or "replace-me" in self.authorization_reference.lower()
        ):
            raise ProposalPolicyError(
                "Sprint 14 live campaign requires a non-placeholder authorization reference"
            )
        if self.max_iterations != 3:
            raise ProposalPolicyError("Sprint 14 campaign requires exactly three iterations")
        if self.max_requests < 4:
            raise ProposalPolicyError("Sprint 14 request budget must allow four bounded requests")
        if len(self.objectives) != 3:
            raise ProposalPolicyError("Sprint 14 campaign requires exactly three objectives")
        ids = [objective.objective_id for objective in self.objectives]
        if len(ids) != len(set(ids)):
            raise ProposalPolicyError("campaign objective identifiers must be unique")
        required_tools = {"http_metadata", "tls_metadata", "well_known_text"}
        if {objective.tool_name for objective in self.objectives} != required_tools:
            raise ProposalPolicyError(
                "Sprint 14 objectives must include HTTP, TLS, and well-known metadata tools"
            )

    @property
    def origin(self) -> str:
        parsed = urlsplit(self.base_url)
        port = parsed.port
        default_port = 443 if parsed.scheme == "https" else 80
        suffix = f":{port}" if port and port != default_port else ""
        return f"{parsed.scheme}://{parsed.hostname}{suffix}"

    @property
    def host(self) -> str:
        parsed = urlsplit(self.base_url)
        if parsed.hostname is None:
            raise ProposalPolicyError("campaign target host is missing")
        return parsed.hostname

    @property
    def port(self) -> int:
        return urlsplit(self.base_url).port or 443

    def remaining(self, completed: set[str]) -> tuple[CampaignObjective, ...]:
        return tuple(
            objective
            for objective in self.objectives
            if objective.objective_id not in completed
        )


@dataclass(frozen=True)
class ProposalDecision:
    allowed: bool
    reasons: tuple[str, ...]

    @property
    def summary(self) -> str:
        return "allowed" if self.allowed else "; ".join(self.reasons)


def build_sprint14_policy(
    *,
    campaign_id: str,
    program_alias: str,
    target_alias: str,
    base_url: str,
    authorization_reference: str,
    operator_approved: bool,
) -> AgentCampaignPolicy:
    parsed = urlsplit(base_url)
    host = parsed.hostname or ""
    port = parsed.port or 443
    origin = f"https://{host}" + (f":{port}" if port != 443 else "")
    objectives = (
        CampaignObjective(
            objective_id="http-root-metadata",
            tool_name="http_metadata",
            arguments={"url": origin + "/"},
        ),
        CampaignObjective(
            objective_id="tls-endpoint-metadata",
            tool_name="tls_metadata",
            arguments={"host": host, "port": port, "server_name": host},
        ),
        CampaignObjective(
            objective_id="robots-security-metadata",
            tool_name="well_known_text",
            arguments={"base_url": origin},
        ),
    )
    return AgentCampaignPolicy(
        campaign_id=campaign_id,
        program_alias=program_alias,
        target_alias=target_alias,
        base_url=base_url,
        authorization_reference=authorization_reference,
        operator_approved=operator_approved,
        objectives=objectives,
    )


def evaluate_model_proposal(
    proposal: ModelProposal,
    policy: AgentCampaignPolicy,
    *,
    completed: set[str],
) -> ProposalDecision:
    reasons: list[str] = []
    if proposal.target_alias != policy.target_alias:
        reasons.append("proposal target alias is outside the active campaign")
    remaining = {item.objective_id: item for item in policy.remaining(completed)}
    objective = remaining.get(proposal.objective_id)
    if objective is None:
        reasons.append("proposal objective is not an approved remaining objective")
    else:
        if proposal.tool_name != objective.tool_name:
            reasons.append("proposal tool does not match the approved objective")
        if proposal.arguments_dict != objective.arguments:
            reasons.append("proposal arguments do not match the approved objective")
    return ProposalDecision(not reasons, tuple(reasons))
