# Sprint 12 Slice 12.6

The submission gate now requires a named human approval bound to the exact report-package digest.
Missing approval, automation identities, rejection, and digest mismatch deny. An approval produces
only an `approved_for_manual_submission` decision; the module has no transport or submission path.
Approval records are integrity-bound and mode `0600`.

Focused validation:

```text
python3 -m pytest -q tests/test_submission_gate.py
6 passed
```

No report was submitted and no external service was contacted.
