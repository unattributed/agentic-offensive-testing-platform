"""Rules-of-engagement model for governed native tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .tool_risk_tiers import ToolRiskTier, parse_risk_tier


class RulesOfEngagementError(ValueError):
    """Raised when tool rules of engagement are unsafe or incomplete."""


@dataclass(frozen=True)
class RulesOfEngagement:
    """Human-defined authority boundary for one active campaign."""

    campaign_id: str
    target_alias: str
    authorization_reference: str
    operator_approved: bool
    allowed_tool_names: frozenset[str]
    allowed_risk_tiers: frozenset[ToolRiskTier]
    allowed_hosts: frozenset[str]
    allowed_ports: frozenset[int] = field(default_factory=frozenset)
    allowed_schemes: frozenset[str] = field(default_factory=lambda: frozenset({"https"}))
    approval_references: dict[str, str] = field(default_factory=dict)
    evidence_classifications: frozenset[str] = field(
        default_factory=lambda: frozenset({"public", "restricted"})
    )

    def __post_init__(self) -> None:
        if not self.campaign_id or not self.target_alias:
            raise RulesOfEngagementError("campaign_id and target_alias are required")
        if not self.authorization_reference.strip():
            raise RulesOfEngagementError("authorization_reference is required")
        if not self.operator_approved:
            raise RulesOfEngagementError("operator approval is required before tool use")
        if not self.allowed_tool_names:
            raise RulesOfEngagementError("at least one native tool must be allowed")
        if not self.allowed_risk_tiers:
            raise RulesOfEngagementError("at least one native tool risk tier must be allowed")
        if not self.allowed_hosts:
            raise RulesOfEngagementError("at least one scoped host must be allowed")
        normalized_tiers = frozenset(parse_risk_tier(tier) for tier in self.allowed_risk_tiers)
        object.__setattr__(self, "allowed_risk_tiers", normalized_tiers)
        for port in self.allowed_ports:
            if not isinstance(port, int) or isinstance(port, bool) or port < 1 or port > 65535:
                raise RulesOfEngagementError("allowed ports must be integers from 1 to 65535")
        for host in self.allowed_hosts:
            if not _is_single_host(host):
                raise RulesOfEngagementError("allowed hosts must be exact single hosts")
        for scheme in self.allowed_schemes:
            if scheme not in {"http", "https"}:
                raise RulesOfEngagementError("allowed schemes must be http or https")
        for classification in self.evidence_classifications:
            if classification not in {"public", "restricted", "secret"}:
                raise RulesOfEngagementError("unsupported evidence classification")

    def allows_tool_name(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tool_names

    def allows_risk_tier(self, risk_tier: str | ToolRiskTier) -> bool:
        return parse_risk_tier(risk_tier) in self.allowed_risk_tiers

    def approval_for(self, key: str) -> str | None:
        value = self.approval_references.get(key)
        if value is None or not value.strip():
            return None
        return value

    def allows_host(self, host: str) -> bool:
        return host.lower().rstrip(".") in {item.lower().rstrip(".") for item in self.allowed_hosts}

    def allows_port(self, port: int) -> bool:
        return not self.allowed_ports or port in self.allowed_ports

    def allows_url(self, url: str) -> tuple[bool, str]:
        parsed = urlsplit(url)
        if parsed.scheme not in self.allowed_schemes:
            return False, "URL scheme is not allowed by ROE"
        if not parsed.hostname or not self.allows_host(parsed.hostname):
            return False, "URL host is outside ROE scope"
        default_port = 443 if parsed.scheme == "https" else 80
        if not self.allows_port(parsed.port or default_port):
            return False, "URL port is outside ROE scope"
        if parsed.username is not None or parsed.password is not None:
            return False, "URL credentials are denied"
        if parsed.query or parsed.fragment:
            return False, "URL query and fragment are denied for governed tools"
        return True, "allowed"


def _is_single_host(host: str) -> bool:
    if not isinstance(host, str) or not host:
        return False
    unsafe = {"/", "*", " ", "\t", "\n", "\r"}
    if any(character in host for character in unsafe):
        return False
    return True
