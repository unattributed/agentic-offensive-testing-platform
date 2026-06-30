# Slice 3.4 evidence: verifier verdicts

Verifier results are separate integrity-checked records restricted to `pass`, `fail`, `inconclusive`, `manual_review`, and `stopped_by_policy`. Pass and fail require explicit evidence references and a verified manifest hash.

`aotp evidence-verdict` creates a private `verification.json` without changing source evidence.

```text
python3 -m pytest tests/test_verifier.py tests/test_evidence_manifest.py tests/test_cli.py
16 passed in 0.23s
```

Tests reject unsupported verdicts, evidence-free pass or fail decisions, and modified verification records.
