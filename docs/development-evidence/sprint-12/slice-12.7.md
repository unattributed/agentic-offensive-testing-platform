# Sprint 12 Slice 12.7

Operator metrics now validate a bounded time period, separate work-hour fields, request and
workflow counts, outcome counts, bounty amount, tool cost, and currency. The schema contains no
target, asset, program, evidence, finding, or personal-data field. Impossible counts and invalid
numeric values fail closed. Local metric files are mode `0600`.

Focused validation:

```text
python3 -m pytest -q tests/test_metrics.py
8 passed
```

Tests use aggregate synthetic values only.
