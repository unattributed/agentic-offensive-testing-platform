# Sprint 11 Slice 11.1

The evaluator script validates the example scope, inventories cases and modules, plans and runs the
two-objective placeholder campaign, verifies the event chain, and generates an evidence-only
report in an isolated ignored workspace.

The script accepts no target, credential, private scope, live flag, or external model. Its summary
proves zero requests, two placeholder evidence records, no report-ready findings, and declared
report limitations.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_evaluator_demo.py
2 passed
```

No target or external service was contacted.
