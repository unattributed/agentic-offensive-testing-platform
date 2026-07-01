# Sprint 10 Slice 10.6

The combined adapter example covers Playwright, ZAP, mitmproxy, OSMAP, and browser-suite using
placeholder aliases only. It contains no target URL, private scope, credential, capture, or
generated evidence.

The strict parser requires every adapter exactly once, `execute: false`, a zero request budget,
the contract default mode, supported capabilities, safe aliases, and complete scope, approval,
evidence, and provenance requirement declarations. Every result is network silent and
`placeholder_not_executable`.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_adapter_examples.py
10 passed
```

Repository safety validation passed. No adapter dependency was imported and no external process or
network action occurred.
