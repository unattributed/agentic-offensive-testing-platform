"""Request budget enforcement for governed native tool calls."""

from __future__ import annotations

from dataclasses import dataclass, field

from .tool_risk_tiers import ToolRiskTier, parse_risk_tier


class RequestBudgetError(ValueError):
    """Raised when a request budget is malformed."""


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    reasons: tuple[str, ...]

    @property
    def summary(self) -> str:
        return "allowed" if self.allowed else "; ".join(self.reasons)


@dataclass(frozen=True)
class BudgetSnapshot:
    max_requests: int
    used_requests: int
    used_by_tool: dict[str, int]
    used_by_risk_tier: dict[str, int]


@dataclass
class RequestBudget:
    """Mutable counter that fails closed before executing any tool."""

    max_requests: int
    per_tool_limits: dict[str, int] = field(default_factory=dict)
    per_risk_tier_limits: dict[ToolRiskTier, int] = field(default_factory=dict)
    used_requests: int = 0
    used_by_tool: dict[str, int] = field(default_factory=dict)
    used_by_risk_tier: dict[ToolRiskTier, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.max_requests, int) or isinstance(self.max_requests, bool) or self.max_requests < 0:
            raise RequestBudgetError("max_requests must be a non-negative integer")
        self.per_risk_tier_limits = {
            parse_risk_tier(tier): limit for tier, limit in self.per_risk_tier_limits.items()
        }
        for name, limit in self.per_tool_limits.items():
            if not name or not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
                raise RequestBudgetError("per-tool limits must be non-negative integers")
        for tier, limit in self.per_risk_tier_limits.items():
            if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
                raise RequestBudgetError(f"risk-tier limit is invalid: {tier}")

    def check(self, *, tool_name: str, risk_tier: str | ToolRiskTier, request_count: int) -> BudgetDecision:
        if not isinstance(request_count, int) or isinstance(request_count, bool) or request_count < 0:
            return BudgetDecision(False, ("request count must be a non-negative integer",))
        tier = parse_risk_tier(risk_tier)
        reasons: list[str] = []
        if self.used_requests + request_count > self.max_requests:
            reasons.append("campaign request budget exceeded")
        tool_limit = self.per_tool_limits.get(tool_name)
        if tool_limit is not None and self.used_by_tool.get(tool_name, 0) + request_count > tool_limit:
            reasons.append("tool request budget exceeded")
        tier_limit = self.per_risk_tier_limits.get(tier)
        if tier_limit is not None and self.used_by_risk_tier.get(tier, 0) + request_count > tier_limit:
            reasons.append("risk-tier request budget exceeded")
        return BudgetDecision(not reasons, tuple(reasons))

    def consume(self, *, tool_name: str, risk_tier: str | ToolRiskTier, request_count: int) -> BudgetDecision:
        decision = self.check(tool_name=tool_name, risk_tier=risk_tier, request_count=request_count)
        if not decision.allowed:
            return decision
        tier = parse_risk_tier(risk_tier)
        self.used_requests += request_count
        self.used_by_tool[tool_name] = self.used_by_tool.get(tool_name, 0) + request_count
        self.used_by_risk_tier[tier] = self.used_by_risk_tier.get(tier, 0) + request_count
        return decision

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            max_requests=self.max_requests,
            used_requests=self.used_requests,
            used_by_tool=dict(sorted(self.used_by_tool.items())),
            used_by_risk_tier={
                tier.value: count
                for tier, count in sorted(self.used_by_risk_tier.items(), key=lambda item: item[0].value)
            },
        )
