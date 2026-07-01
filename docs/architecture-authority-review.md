# Architecture authority review

## Review conclusion

No execution path bypasses the deterministic policy decision. The CLI case path and campaign loop
are the only executor importers, and every executor call is nested under `decision.allowed`.
LangGraph delegates each step to the same campaign loop and does not import the executor.

This review proves the v0.1 baseline. It does not require future adapters to remain stubs. The
post-Sprint 13 architecture preserves the same invariant by placing the deterministic policy gate
between Deep Agent proposals and every campaign-governed native tool invocation.

## Authority matrix

| Component | May propose | May authorize execution | May send requests |
|---|---:|---:|---:|
| Program profile and private scope | no | supplies authority inputs | no |
| Scheduler | selects approved objective order | no | no |
| Local model planner or Deep Agent | proposes structured objectives and tool calls | no | only through an allowed native tool invocation |
| Policy gate | no | yes, sole decision point | no |
| Deterministic executor | no | no | no in v0.1; governed execution after tool acceptance |
| Native tool registry and wrappers | typed capabilities and execution | no | yes, only after policy and approval |
| Evidence and verifier pipeline | verdict records from evidence | no | no |
| Reporter | evidence-bound draft language | no | no |
| Human reviewer | lifecycle and report review decisions | no technical bypass | no |

## Data flow review

1. Private authorization documents and scope are parsed independently.
2. Campaign parsing and scheduling can select only declared objectives.
3. Model planning can return only an already approved objective ID.
4. Policy evaluates scope, action, approvals, budgets, paths, redaction, and stop conditions.
5. A denied decision creates stopped-by-policy evidence without calling the executor.
6. An allowed decision reaches the deterministic executor, which returns zero-request local
   results or a zero-request manual-review live stub.
7. Evidence is written and integrity hashed before campaign checkpoint advancement.
8. Verification and candidate lifecycle require evidence hashes and human transitions.
9. Reporting loads and re-verifies evidence and eligible candidates. It accepts no free-form model
   facts or authorization input.

## Bypass checklist

- [x] Executor imports are limited to the CLI case path and campaign loop.
- [x] Every executor call is guarded by `decision.allowed`.
- [x] v0.1 live execution returns a manual-review stub with zero requests.
- [x] Post-Sprint 13 live execution remains blocked until native tool risk, scope, budget, approval,
  and evidence controls accept the invocation.
- [x] LangGraph uses the deterministic campaign loop.
- [x] Model output cannot set scope, policy, authorization, verdict, confidence, impact, or
  severity.
- [x] Deferred adapters have live execution disabled and zero default request budgets.
- [x] Reporter input is limited to evidence and optional finding paths.
- [x] Automatic report submission does not exist.
- [x] Generated state, evidence, reports, checkpoints, screenshots, traces, and private files are
  ignored.

The review is enforced by `tests/test_architecture_authority.py` and the existing policy,
orchestration, evidence, lifecycle, and reporter suites.
