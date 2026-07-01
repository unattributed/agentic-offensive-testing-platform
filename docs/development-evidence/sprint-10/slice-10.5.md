# Sprint 10 Slice 10.5

The browser-suite contract is external-reference-only. It accepts an approved artifact class,
safe source commit and license review aliases, and a redacted, hashed, relative evidence
reference. No code is imported and no process is invoked.

The separately cloned source project declares `AGPL-3.0-or-later`. AOTP records that fact and
requires separate license review. Vendoring, dependency import, license-boundary blending,
unredacted model input, generated evidence commitment, and implicit execution are denied.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_browser_suite_contract.py
9 passed
```

The adjacent browser-suite repository was inspected read-only. No code or generated evidence was
copied.
