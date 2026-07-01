# Sprint 11 Slice 11.2

The tracked dry-run sample is a normalized placeholder summary, not assessment evidence. It
excludes variable timestamps, identifiers, paths, and hashes while preserving the safety-relevant
result.

The evaluator demo test compares each generated summary byte-for-structure with the tracked sample.
Generated state, events, manifests, and reports remain ignored under `.aotp/`.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_evaluator_demo.py
2 passed
```

The sample records zero requests and contains no target or private data.
