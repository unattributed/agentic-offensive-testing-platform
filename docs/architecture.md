# Architecture

AOTP separates authority, planning, execution, evidence, verification, and reporting. The settled
post-Sprint 13 architecture uses a local Ollama model and LangChain Deep Agents without MCP.

```text
Ollama local model
  -> LangChain Deep Agent supervisor
  -> AOTP subagents and skills
  -> campaign-governed native tool registry
  -> policy gate and human approval steering
  -> FOSS adapters and Parrot tools
  -> evidence archive, sensitive vault, analysis, PoC, report package
```

Program policy context and technical scope are separate. The policy gate is the sole execution authority. Planner output has no authority. Adapters declare supported, required, and denied actions. The executor is deterministic, and the foundational release is network-silent.

After Sprint 13, the Deep Agent may propose objectives and invoke real native tools only after the
deterministic control plane validates the active campaign, ROE, scope, tool risk tier, arguments,
budgets, evidence classification, and required approval. Denials are evidence. High-risk action
requires explicit ROE and/or human approval. Submission and disclosure remain manual-only.

The evidence archive is the normal evidence plane. Sensitive proof and campaign key material use
encrypted campaign storage. The agent and approved tools may access raw vault material when the
active campaign ROE and artifact classification authorize it; every access is purpose-bound and
logged, and retention, export, report inclusion, and annex creation are separately controlled.

State and evidence are local, ignored artifacts. Reports read those artifacts and do not receive free-form facts from a model.

## LangGraph orchestration

LangGraph is the durable orchestration implementation around the deterministic state and policy contracts. Its SQLite checkpoint persistence and interrupt model provide campaign pause, approval, process restart, and recovery. Policy evaluation and deterministic adapters remain outside model control.

The graph preserves JSON state compatibility, idempotent step behavior, stable campaign and iteration identifiers, policy decisions before side effects, and evidence commits before checkpoint advancement. See [langgraph-orchestration.md](langgraph-orchestration.md).

The v0.1 authority and bypass review is recorded in
[architecture-authority-review.md](architecture-authority-review.md).

The complete post-Sprint 13 component and control flow is documented in
[agentic-architecture.md](agentic-architecture.md).
