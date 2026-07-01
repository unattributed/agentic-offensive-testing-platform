# Sprint 12 Slice 12.5

Report packaging now copies a redaction-checked draft into a private mode `0700` directory and
binds it to verified evidence-manifest hashes. The package manifest and draft are mode `0600`.
Every package is fixed to draft status, pending human review, and manual-only submission.

Focused validation:

```text
python3 -m pytest -q tests/test_report_package.py
4 passed
```

Tests prove draft and manifest tampering fail closed and secret-bearing report text is rejected.
