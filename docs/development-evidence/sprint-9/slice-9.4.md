# Sprint 9 Slice 9.4

Verification assistance receives only reference-bound evidence summaries and can return only a
summary, cited evidence references, and uncertainty. It cannot set verdict, confidence,
authorization, or policy.

Report assistance can return only a title, draft summary, cited evidence references, and caveat. It
cannot set severity, impact, authorization, or policy. Unknown or invented evidence references are
rejected independently of the response schema.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_model_assistance.py
15 passed
```

All model calls used an in-memory stub. No service or target was contacted.
