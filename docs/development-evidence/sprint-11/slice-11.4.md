# Sprint 11 Slice 11.4

The architecture review maps authority and data flow from private scope through policy, execution,
evidence, lifecycle, and reporting. Static enforcement proves the CLI and campaign loop are the
only executor importers and every executor call is guarded by `decision.allowed`.

The review also proves the live boundary remains a zero-request manual-review stub, LangGraph
delegates to the deterministic loop, model and deferred adapter output has no authority, and the
reporter accepts only evidence and finding paths.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_architecture_authority.py
6 passed
```

No bypass path was identified.
