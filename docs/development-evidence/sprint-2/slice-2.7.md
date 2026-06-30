# Slice 2.7 evidence: durable LangGraph orchestration

## Functional result

`LangGraphCampaignOrchestrator` executes one reference-engine objective per graph step. The deterministic engine continues to own policy, evidence, request budgets, state integrity, and event hashes. LangGraph provides durable routing, SQLite checkpoints, process restart, and interrupt-based review.

Checkpoint state contains aliases, hashes, status, and local state references rather than the private scope or profile. The checkpoint directory is mode `0700`; database, WAL, and shared-memory files are mode `0600`.

## Validation

```bash
python3 -m pytest tests/test_langgraph_orchestration.py tests/test_cli.py
```

```text
10 passed in 0.28s
```

Tests prove completion parity, policy-stop parity, SQLite restart and reviewed resume, event-chain validity after resume, checkpoint permissions, absence of scope-document content in SQLite, and the `campaign-graph-run` CLI.

Validated direct versions:

- LangGraph 1.2.7
- langgraph-checkpoint-sqlite 3.1.0

No LangSmith tracing, agent server, remote model, or telemetry is configured.
