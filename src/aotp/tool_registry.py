"""Campaign-governed native tool registry."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from .agent_workspace import AgentCampaignWorkspace
from .evidence import utc_now
from .request_budget import BudgetDecision, RequestBudget
from .roe import RulesOfEngagement
from .tool_risk_tiers import ToolRiskTier, parse_risk_tier, risk_tier_definition


class ToolRegistryError(ValueError):
    """Raised when a native tool registry configuration is invalid."""


class ToolExecutionDenied(RuntimeError):
    """Raised when a governed native tool call is denied before execution."""


@dataclass(frozen=True)
class ToolArgument:
    name: str
    value_type: type | tuple[type, ...]
    required: bool = True

    def validate(self, arguments: dict[str, Any]) -> tuple[str, ...]:
        if self.required and self.name not in arguments:
            return (f"missing required argument: {self.name}",)
        if self.name not in arguments:
            return ()
        value = arguments[self.name]
        if isinstance(value, bool) and self.value_type is int:
            return (f"argument has invalid type: {self.name}",)
        if not isinstance(value, self.value_type):
            return (f"argument has invalid type: {self.name}",)
        return ()


ToolScopeValidator = Callable[[dict[str, Any], RulesOfEngagement], tuple[str, ...]]
ToolExecutor = Callable[[dict[str, Any]], dict[str, Any]]
RequestCost = int | Callable[[dict[str, Any]], int]


@dataclass(frozen=True)
class NativeToolSpec:
    name: str
    description: str
    risk_tier: ToolRiskTier
    arguments: tuple[ToolArgument, ...]
    request_cost: RequestCost
    evidence_classification: str
    executor: ToolExecutor | None = None
    scope_validator: ToolScopeValidator | None = None
    required_approval_key: str | None = None
    external_tools: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", self.name) is None:
            raise ToolRegistryError("native tool name must be a safe identifier")
        parse_risk_tier(self.risk_tier)
        if self.evidence_classification not in {"public", "restricted", "secret"}:
            raise ToolRegistryError("unsupported evidence classification")
        names = [argument.name for argument in self.arguments]
        if len(names) != len(set(names)):
            raise ToolRegistryError("native tool argument names must be unique")
        if isinstance(self.request_cost, int):
            if isinstance(self.request_cost, bool) or self.request_cost < 0:
                raise ToolRegistryError("native tool request cost must be non-negative")

    def argument_names(self) -> set[str]:
        return {argument.name for argument in self.arguments}

    def validate_arguments(self, arguments: dict[str, Any]) -> tuple[str, ...]:
        if not isinstance(arguments, dict):
            return ("tool arguments must be a mapping",)
        reasons: list[str] = []
        unknown = sorted(set(arguments) - self.argument_names())
        if unknown:
            reasons.append("unknown tool arguments: " + ", ".join(unknown))
        for argument in self.arguments:
            reasons.extend(argument.validate(arguments))
        return tuple(reasons)

    def cost_for(self, arguments: dict[str, Any]) -> int:
        value = self.request_cost(arguments) if callable(self.request_cost) else self.request_cost
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ToolRegistryError("native tool request cost resolved to an invalid value")
        return value


@dataclass(frozen=True)
class NativeToolCall:
    campaign_id: str
    target_alias: str
    tool_name: str
    arguments: dict[str, Any]
    proposal_id: str = "manual"
    requested_by: str = "agent"


@dataclass(frozen=True)
class ToolCallDecision:
    allowed: bool
    reasons: tuple[str, ...]
    tool_name: str
    risk_tier: str | None
    request_count: int
    evidence_classification: str | None

    @property
    def summary(self) -> str:
        return "allowed" if self.allowed else "; ".join(self.reasons)


@dataclass(frozen=True)
class NativeToolResult:
    tool_name: str
    risk_tier: str
    request_count: int
    evidence_classification: str
    result: dict[str, Any]
    evidence_path: str | None = None


class NativeToolRegistry:
    """Typed native tool resolver with ROE, budget, and denial evidence hooks."""

    def __init__(self, specs: tuple[NativeToolSpec, ...] = ()) -> None:
        self._specs: dict[str, NativeToolSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: NativeToolSpec) -> None:
        if spec.name in self._specs:
            raise ToolRegistryError(f"duplicate native tool registration: {spec.name}")
        self._specs[spec.name] = spec

    def resolve(self, tool_name: str) -> NativeToolSpec:
        try:
            return self._specs[tool_name]
        except KeyError as exc:
            raise ToolRegistryError(f"unregistered native tool: {tool_name}") from exc

    def list_specs(self) -> tuple[NativeToolSpec, ...]:
        return tuple(self._specs[name] for name in sorted(self._specs))

    def evaluate(
        self,
        call: NativeToolCall,
        roe: RulesOfEngagement,
        budget: RequestBudget,
    ) -> ToolCallDecision:
        reasons: list[str] = []
        spec = self._specs.get(call.tool_name)
        if spec is None:
            return ToolCallDecision(
                False,
                ("native tool is not registered",),
                call.tool_name,
                None,
                0,
                None,
            )
        request_count = 0
        if call.campaign_id != roe.campaign_id:
            reasons.append("tool call campaign does not match active ROE")
        if call.target_alias != roe.target_alias:
            reasons.append("tool call target alias is outside active ROE")
        if not roe.allows_tool_name(spec.name):
            reasons.append("native tool is not allowed by ROE")
        if not roe.allows_risk_tier(spec.risk_tier):
            reasons.append("native tool risk tier is not allowed by ROE")
        tier_definition = risk_tier_definition(spec.risk_tier)
        if tier_definition.requires_human_approval and spec.required_approval_key:
            if roe.approval_for(spec.required_approval_key) is None:
                reasons.append("required human approval reference is missing")
        if spec.evidence_classification not in roe.evidence_classifications:
            reasons.append("tool evidence classification is not allowed by ROE")
        reasons.extend(spec.validate_arguments(call.arguments))
        if spec.scope_validator is not None:
            reasons.extend(spec.scope_validator(call.arguments, roe))
        try:
            request_count = spec.cost_for(call.arguments)
        except ToolRegistryError as exc:
            reasons.append(str(exc))
        if not reasons:
            budget_decision: BudgetDecision = budget.check(
                tool_name=spec.name,
                risk_tier=spec.risk_tier,
                request_count=request_count,
            )
            reasons.extend(budget_decision.reasons)
        return ToolCallDecision(
            not reasons,
            tuple(reasons),
            spec.name,
            spec.risk_tier.value,
            request_count,
            spec.evidence_classification,
        )

    def execute(
        self,
        call: NativeToolCall,
        roe: RulesOfEngagement,
        budget: RequestBudget,
        *,
        workspace: AgentCampaignWorkspace | None = None,
    ) -> NativeToolResult:
        decision = self.evaluate(call, roe, budget)
        if not decision.allowed:
            if workspace is not None:
                write_denied_tool_call_evidence(workspace, call, decision, roe)
            raise ToolExecutionDenied(decision.summary)
        spec = self.resolve(call.tool_name)
        if spec.executor is None:
            raise ToolRegistryError(f"native tool has no executor: {call.tool_name}")
        consume_decision = budget.consume(
            tool_name=spec.name,
            risk_tier=spec.risk_tier,
            request_count=decision.request_count,
        )
        if not consume_decision.allowed:
            raise ToolRegistryError("request budget changed before consume")
        result = spec.executor(call.arguments)
        evidence_path = None
        if workspace is not None:
            artifact = write_executed_tool_call_evidence(workspace, call, decision, roe, result)
            evidence_path = str(artifact.relative_to(workspace.path))
        return NativeToolResult(
            tool_name=spec.name,
            risk_tier=spec.risk_tier.value,
            request_count=decision.request_count,
            evidence_classification=spec.evidence_classification,
            result=result,
            evidence_path=evidence_path,
        )


def denied_tool_call_record(
    call: NativeToolCall,
    decision: ToolCallDecision,
    roe: RulesOfEngagement,
) -> dict[str, Any]:
    """Build a deterministic evidence record for a denied tool call."""

    return {
        "schema_version": "1.0",
        "timestamp_utc": utc_now(),
        "campaign_id": call.campaign_id,
        "active_campaign_id": roe.campaign_id,
        "target_alias": call.target_alias,
        "active_target_alias": roe.target_alias,
        "tool_name": call.tool_name,
        "proposal_id": call.proposal_id,
        "requested_by": call.requested_by,
        "proposal_arguments": _redact_tool_arguments(call.arguments),
        "allowed": False,
        "executed": False,
        "risk_tier": decision.risk_tier,
        "request_count": decision.request_count,
        "denial_reasons": decision.reasons,
        "policy_decision": decision.summary,
    }


def write_denied_tool_call_evidence(
    workspace: AgentCampaignWorkspace,
    call: NativeToolCall,
    decision: ToolCallDecision,
    roe: RulesOfEngagement,
):
    safe_tool = re.sub(r"[^a-z0-9._-]+", "-", call.tool_name.lower()).strip("-") or "tool"
    return workspace.write_json(
        "evidence",
        f"denied-{safe_tool}-{uuid.uuid4().hex[:12]}",
        denied_tool_call_record(call, decision, roe),
    )


def executed_tool_call_record(
    call: NativeToolCall,
    decision: ToolCallDecision,
    roe: RulesOfEngagement,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Build a deterministic evidence record for a successful governed tool call."""

    return {
        "schema_version": "1.0",
        "timestamp_utc": utc_now(),
        "campaign_id": call.campaign_id,
        "active_campaign_id": roe.campaign_id,
        "target_alias": call.target_alias,
        "active_target_alias": roe.target_alias,
        "tool_name": call.tool_name,
        "proposal_id": call.proposal_id,
        "requested_by": call.requested_by,
        "proposal_arguments": _redact_tool_arguments(call.arguments),
        "allowed": True,
        "executed": True,
        "risk_tier": decision.risk_tier,
        "request_count": decision.request_count,
        "evidence_classification": decision.evidence_classification,
        "policy_decision": decision.summary,
        "result": result,
    }


def write_executed_tool_call_evidence(
    workspace: AgentCampaignWorkspace,
    call: NativeToolCall,
    decision: ToolCallDecision,
    roe: RulesOfEngagement,
    result: dict[str, Any],
):
    safe_tool = re.sub(r"[^a-z0-9._-]+", "-", call.tool_name.lower()).strip("-") or "tool"
    return workspace.write_json(
        "evidence",
        f"executed-{safe_tool}-{uuid.uuid4().hex[:12]}",
        executed_tool_call_record(call, decision, roe, result),
    )


def _redact_tool_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    sensitive_names = ("authorization", "bearer", "cookie", "password", "secret", "session", "token")
    for key, value in arguments.items():
        key_text = str(key).lower()
        if any(marker in key_text for marker in sensitive_names):
            safe[key] = "<redacted>"
            continue
        if isinstance(value, str):
            parsed = urlsplit(value)
            if parsed.scheme and (parsed.username is not None or parsed.password is not None):
                safe[key] = "<redacted-url-credentials>"
                continue
        safe[key] = value
    return safe


def _url_scope_validator(argument_name: str) -> ToolScopeValidator:
    def validate(arguments: dict[str, Any], roe: RulesOfEngagement) -> tuple[str, ...]:
        allowed, reason = roe.allows_url(str(arguments.get(argument_name, "")))
        return () if allowed else (reason,)

    return validate


def _tls_scope_validator(arguments: dict[str, Any], roe: RulesOfEngagement) -> tuple[str, ...]:
    host = str(arguments.get("host", ""))
    server_name = str(arguments.get("server_name", ""))
    port = arguments.get("port")
    reasons: list[str] = []
    if host != server_name:
        reasons.append("TLS server_name must match host")
    if not roe.allows_host(host):
        reasons.append("TLS host is outside ROE scope")
    if isinstance(port, int) and not isinstance(port, bool):
        if not roe.allows_port(port):
            reasons.append("TLS port is outside ROE scope")
    return tuple(reasons)


def _host_port_scope_validator(arguments: dict[str, Any], roe: RulesOfEngagement) -> tuple[str, ...]:
    host = str(arguments.get("host", ""))
    port = arguments.get("port")
    reasons: list[str] = []
    if not roe.allows_host(host):
        reasons.append("host is outside ROE scope")
    if isinstance(port, int) and not isinstance(port, bool) and not roe.allows_port(port):
        reasons.append("port is outside ROE scope")
    return tuple(reasons)


def _well_known_cost(_arguments: dict[str, Any]) -> int:
    return 2


def _single_request(_arguments: dict[str, Any]) -> int:
    return 1


def _no_network(_arguments: dict[str, Any]) -> int:
    return 0


def build_default_native_tool_registry() -> NativeToolRegistry:
    """Return the Sprint 15 registry without granting authority to any caller."""

    from .agent_tools.campaign_shell import run_campaign_shell_command
    from .agent_tools.http_metadata import fetch_http_metadata, fetch_well_known_metadata
    from .agent_tools.nmap_governed import run_governed_nmap
    from .agent_tools.playwright_passive import collect_playwright_passive_metadata
    from .agent_tools.tls_metadata import fetch_tls_metadata
    from .agent_tools.zap_passive import run_zap_passive_baseline

    return NativeToolRegistry(
        (
            NativeToolSpec(
                name="http_metadata",
                description="single credential-free HTTP metadata request",
                risk_tier=ToolRiskTier.PASSIVE_METADATA,
                arguments=(ToolArgument("url", str),),
                request_cost=_single_request,
                evidence_classification="public",
                scope_validator=_url_scope_validator("url"),
                executor=lambda args: fetch_http_metadata(args["url"]).result,
            ),
            NativeToolSpec(
                name="well_known_text",
                description="robots.txt and security.txt metadata collection",
                risk_tier=ToolRiskTier.PASSIVE_METADATA,
                arguments=(ToolArgument("base_url", str),),
                request_cost=_well_known_cost,
                evidence_classification="public",
                scope_validator=_url_scope_validator("base_url"),
                executor=lambda args: fetch_well_known_metadata(args["base_url"]).result,
            ),
            NativeToolSpec(
                name="tls_metadata",
                description="single TLS endpoint metadata observation",
                risk_tier=ToolRiskTier.PASSIVE_METADATA,
                arguments=(ToolArgument("host", str), ToolArgument("port", int), ToolArgument("server_name", str)),
                request_cost=_single_request,
                evidence_classification="public",
                scope_validator=_tls_scope_validator,
                executor=lambda args: fetch_tls_metadata(args["host"], args["port"], args["server_name"]).result,
            ),
            NativeToolSpec(
                name="campaign_shell",
                description="constrained local shell dispatcher for allowlisted inventory commands",
                risk_tier=ToolRiskTier.PASSIVE_METADATA,
                arguments=(ToolArgument("command_id", str),),
                request_cost=_no_network,
                evidence_classification="public",
                executor=lambda args: run_campaign_shell_command(args["command_id"]).result,
            ),
            NativeToolSpec(
                name="nmap_governed",
                description="single-host single-service nmap fingerprint wrapper",
                risk_tier=ToolRiskTier.SERVICE_FINGERPRINT,
                arguments=(ToolArgument("host", str), ToolArgument("port", int), ToolArgument("service_name", str)),
                request_cost=_single_request,
                evidence_classification="restricted",
                scope_validator=_host_port_scope_validator,
                required_approval_key="service_fingerprint",
                external_tools=("nmap",),
                executor=lambda args: run_governed_nmap(args["host"], args["port"], args["service_name"]).result,
            ),
            NativeToolSpec(
                name="zap_passive_baseline",
                description="OWASP ZAP passive baseline wrapper",
                risk_tier=ToolRiskTier.PASSIVE_SCANNER,
                arguments=(ToolArgument("target_url", str), ToolArgument("max_minutes", int)),
                request_cost=_single_request,
                evidence_classification="restricted",
                scope_validator=_url_scope_validator("target_url"),
                external_tools=("zap-baseline.py",),
                executor=lambda args: run_zap_passive_baseline(args["target_url"], max_minutes=args["max_minutes"]).result,
            ),
            NativeToolSpec(
                name="playwright_passive_metadata",
                description="single-page Playwright passive browser metadata wrapper",
                risk_tier=ToolRiskTier.PASSIVE_BROWSER,
                arguments=(ToolArgument("url", str),),
                request_cost=_single_request,
                evidence_classification="public",
                scope_validator=_url_scope_validator("url"),
                external_tools=("playwright",),
                executor=lambda args: collect_playwright_passive_metadata(args["url"]).result,
            ),
        )
    )
