"""LangChain Deep Agent supervisor for bounded Sprint 14 proposals."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Protocol

from deepagents import create_deep_agent
from deepagents.backends import StateBackend

from ..model_proposal_gate import CampaignObjective
from ..model_proposals import ModelProposal, parse_model_proposal
from .bootstrap import OllamaBootstrap, OllamaRuntimeStatus
from .subagents import sprint14_subagents


SYSTEM_PROMPT = """You are the AOTP Sprint 14 campaign supervisor.
Operate only inside the supplied authorized campaign context.
Select exactly one approved remaining objective per turn.
Return the required structured response.
Do not alter tool arguments, add targets, request credentials, use shell commands, submit reports,
or infer findings. AOTP policy decides whether the proposal executes.
"""


class ProposalSupervisor(Protocol):
    def start(self) -> "SupervisorStatus": ...

    def propose(
        self,
        *,
        target_alias: str,
        remaining: tuple[CampaignObjective, ...],
        evidence_summaries: list[dict[str, Any]],
    ) -> ModelProposal: ...


@dataclass(frozen=True)
class SupervisorStatus:
    framework: str
    model: str
    model_digest: str
    subagents: tuple[str, ...]
    started: bool


class AOTPDeepAgentSupervisor:
    def __init__(
        self,
        bootstrap: OllamaBootstrap,
        *,
        agent_factory: Callable[..., Any] = create_deep_agent,
    ) -> None:
        self.bootstrap = bootstrap
        self.agent_factory = agent_factory
        self.runtime: OllamaRuntimeStatus | None = None
        self.agent: Any | None = None
        self.subagent_specs: tuple[dict[str, Any], ...] = ()

    def start(self) -> SupervisorStatus:
        if self.agent is None:
            model = self.bootstrap.build_model()
            self.runtime = self.bootstrap.validate()
            self.subagent_specs = sprint14_subagents(model)
            self.agent = self.agent_factory(
                model=model,
                tools=[],
                system_prompt=SYSTEM_PROMPT,
                backend=StateBackend(),
                response_format=ModelProposal,
                name="aotp-sprint14-supervisor",
            )
        if self.runtime is None:
            raise RuntimeError("Deep Agent supervisor runtime did not initialize")
        return SupervisorStatus(
            framework="langchain-deep-agents",
            model=self.runtime.model,
            model_digest=self.runtime.model_digest,
            subagents=tuple(spec["name"] for spec in self.subagent_specs),
            started=True,
        )

    def propose(
        self,
        *,
        target_alias: str,
        remaining: tuple[CampaignObjective, ...],
        evidence_summaries: list[dict[str, Any]],
    ) -> ModelProposal:
        if self.agent is None:
            raise RuntimeError("Deep Agent supervisor must be started before proposing")
        context = {
            "target_alias": target_alias,
            "remaining_objectives": [
                objective.as_model_context() for objective in remaining
            ],
            "classified_evidence_summaries": evidence_summaries,
            "instruction": (
                "Choose one remaining objective. Copy its tool and arguments exactly. "
                "Explain briefly how it improves campaign coverage."
            ),
        }
        request = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Produce the next AOTP campaign proposal from this bounded context: "
                        + json.dumps(context, sort_keys=True, separators=(",", ":"))
                    ),
                }
            ]
        }
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                result = self.agent.invoke(request, {"recursion_limit": 20})
                if not isinstance(result, dict) or "structured_response" not in result:
                    raise RuntimeError("Deep Agent did not return a structured proposal")
                return parse_model_proposal(result["structured_response"])
            except Exception as exc:
                last_error = exc
        raise RuntimeError(
            "Deep Agent did not return a structured proposal after two bounded attempts"
        ) from last_error
