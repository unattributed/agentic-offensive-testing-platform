# Architecture

AOTP separates authority, planning, execution, evidence, verification, and reporting.

```text
program profile -> private scope -> campaign parser -> scheduler
                                             |
AI advisory output --------------------------+
                                             v
                                        policy gate
                                     deny /       \ allow
                               stop record         adapter
                                                      |
                                             evidence writer
                                                      |
                                          verifier + lifecycle
                                                      |
                                              human approval
                                                      |
                                           evidence-only report
```

Program policy context and technical scope are separate. The policy gate is the sole execution authority. Planner output has no authority. Adapters declare supported, required, and denied actions. The executor is deterministic, and the foundational release is network-silent.

State and evidence are local, ignored artifacts. Reports read those artifacts and do not receive free-form facts from a model.

## LangGraph orchestration

LangGraph is the durable orchestration implementation around the deterministic state and policy contracts. Its SQLite checkpoint persistence and interrupt model provide campaign pause, approval, process restart, and recovery. Policy evaluation and deterministic adapters remain outside model control.

The graph preserves JSON state compatibility, idempotent step behavior, stable campaign and iteration identifiers, policy decisions before side effects, and evidence commits before checkpoint advancement. See [langgraph-orchestration.md](langgraph-orchestration.md).
