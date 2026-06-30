# Sprint 2 closeout evidence

Sprint 2 delivers a strict, bounded, checkpointed campaign engine with real state integrity, reviewed pause and resume, stop controls, event verification, and durable LangGraph orchestration.

## Slice commits

| Slice | Commit | Functional result |
|---|---|---|
| 2.1 campaign parser | `8fb7fa0` | Strict execution contract and dependency graph validation |
| 2.2 campaign state | `916106f` | Atomic private checkpoints with canonical integrity digest |
| 2.3 campaign loop | `b897f47` | One-objective checkpoints, stable run IDs, evidence before state advancement, and safe continuation |
| 2.4 scheduler and budgets | `9e0a2f1` | Dependency-aware order and predictive iteration, runtime, request, rate, and failure stops |
| 2.5 pause, resume, stop | `4589aff` | Checkpoint-bound private review decisions and persistent operator stops |
| 2.6 event log | `f8f3726` | Append-only hash-chained JSONL audit history |
| 2.7 LangGraph | `ec79142` | Durable SQLite graph checkpoints, interrupts, restart, and deterministic parity |

Each slice has a focused evidence record in this directory.

## Full validation

```bash
make check
python3 -m pip check
```

```text
python3 -m compileall -q src tests
python3 -m pytest
99 passed in 0.56s
./scripts/validate-repository-safety.sh
repository safety validation passed
No broken requirements found.
```

## Functional smoke

An isolated CLI invocation of `campaign-graph-run`:

- completed the two-objective dry-run campaign;
- created a mode-`0600` SQLite checkpoint;
- created integrity-checked AOTP state;
- produced evidence for both objectives;
- passed `campaign-events-verify`; and
- passed `evidence-verify`.

An attempted checkpoint path outside the workspace was denied. This boundary also has a regression test.

## Sprint acceptance

- Campaign planning rejects malformed, cyclic, unsafe, or live-by-default definitions.
- State records completed, pending, skipped, and stopped dispositions without overlap.
- Every execution, policy denial, and budget stop writes evidence.
- Resume rejects changed scope or campaign definitions.
- Human approval is bound to the exact checkpoint and objective.
- Operator stop is persistent.
- Event modification or chain discontinuity is detected.
- LangGraph completion and policy stops match the deterministic engine.
- SQLite checkpoints survive process restart without storing private scope documents.
- No adapter in this sprint sends live target traffic.
