# Sprint 6 Slice 6.5: network-silent dry-run execution

The deterministic executor produces a bounded fuzzing plan with payload classes, counts, endpoint
budgets, response, retry, and runtime ceilings, and an optional corpus reference. Execution is
marked `not_executed`, actual request count remains zero, and `fuzzing-evidence.json` is registered
and hashed in the evidence manifest.
