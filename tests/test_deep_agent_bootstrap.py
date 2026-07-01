from __future__ import annotations

import json

import pytest

from aotp.deep_agent.bootstrap import OllamaBootstrap, OllamaBootstrapError
from aotp.deep_agent.supervisor import AOTPDeepAgentSupervisor
from aotp.model_proposals import ModelProposal


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit):
        return self.payload[:limit]


def _inventory(capabilities=None):
    return {
        "models": [
            {
                "name": "local-tools:latest",
                "model": "local-tools:latest",
                "digest": "a" * 64,
                "capabilities": capabilities or ["completion", "tools"],
            }
        ]
    }


def test_bootstrap_requires_127001_and_installed_tool_model():
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse(_inventory())

    status = OllamaBootstrap(
        model="local-tools:latest",
        opener=opener,
    ).validate()
    assert status.available is True
    assert status.base_url == "http://127.0.0.1:11434"
    assert "tools" in status.capabilities
    assert captured == {
        "url": "http://127.0.0.1:11434/api/tags",
        "timeout": 10,
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:11434",
        "http://0.0.0.0:11434",
        "https://127.0.0.1:11434",
        "http://user:pass@127.0.0.1:11434",
        "http://127.0.0.1:11434/api",
    ],
)
def test_bootstrap_rejects_noncanonical_or_credentialed_endpoint(url):
    with pytest.raises(OllamaBootstrapError, match="127.0.0.1"):
        OllamaBootstrap(base_url=url)


def test_bootstrap_rejects_missing_or_non_tool_model():
    with pytest.raises(OllamaBootstrapError, match="not installed"):
        OllamaBootstrap(
            model="missing:latest",
            opener=lambda *_args, **_kwargs: FakeResponse(_inventory()),
        ).validate()


def test_bootstrap_rejects_invalid_gpu_count():
    with pytest.raises(OllamaBootstrapError, match="GPU count"):
        OllamaBootstrap(num_gpu=-1)
    with pytest.raises(OllamaBootstrapError, match="tool-calling"):
        OllamaBootstrap(
            model="local-tools:latest",
            opener=lambda *_args, **_kwargs: FakeResponse(
                _inventory(["completion"])
            ),
        ).validate()


class FakeBootstrap:
    def build_model(self):
        return object()

    def validate(self):
        return type(
            "Status",
            (),
            {
                "model": "local-tools:latest",
                "model_digest": "a" * 64,
            },
        )()


class FakeAgent:
    calls = 0

    def invoke(self, *_args, **_kwargs):
        self.calls += 1
        return {
            "structured_response": ModelProposal(
                objective_id="http-root-metadata",
                tool_name="http_metadata",
                target_alias="owned-mail",
                arguments={"url": "https://mail.example.invalid/"},
                rationale="Collect approved metadata.",
            )
        }


def test_supervisor_starts_with_three_subagents_and_returns_structured_proposal():
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return FakeAgent()

    supervisor = AOTPDeepAgentSupervisor(FakeBootstrap(), agent_factory=factory)
    status = supervisor.start()
    assert status.started is True
    assert status.framework == "langchain-deep-agents"
    assert status.subagents == (
        "campaign-planner",
        "evidence-analyst",
        "report-drafter",
    )
    assert captured["tools"] == []
    assert "subagents" not in captured
    assert captured["response_format"] is ModelProposal
    proposal = supervisor.propose(
        target_alias="owned-mail",
        remaining=(),
        evidence_summaries=[],
    )
    assert proposal.tool_name == "http_metadata"


class RetryAgent(FakeAgent):
    def invoke(self, *_args, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            raise ValueError("transient local model stream failure")
        return {
            "structured_response": ModelProposal(
                objective_id="http-root-metadata",
                tool_name="http_metadata",
                target_alias="owned-mail",
                arguments={"url": "https://mail.example.invalid/"},
                rationale="Collect approved metadata.",
            )
        }


def test_supervisor_retries_one_transient_local_model_failure():
    agent = RetryAgent()
    supervisor = AOTPDeepAgentSupervisor(
        FakeBootstrap(),
        agent_factory=lambda **_kwargs: agent,
    )
    supervisor.start()
    proposal = supervisor.propose(
        target_alias="owned-mail",
        remaining=(),
        evidence_summaries=[],
    )
    assert proposal.objective_id == "http-root-metadata"
    assert agent.calls == 2
