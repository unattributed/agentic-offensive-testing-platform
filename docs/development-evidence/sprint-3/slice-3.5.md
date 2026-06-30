# Slice 3.5 evidence: finding candidates

Finding candidates now require a verified evidence manifest, matching fail-verdict record, evidence and verification hashes, stable fingerprint, target and case aliases, independent severity, confidence and evidence strength, and lifecycle history.

Only `fail` can create a candidate. Confirmation requires human validation; report readiness additionally requires rated severity and non-weak evidence. Candidate files are integrity checked and mode `0600`.

```text
python3 -m pytest tests/test_finding_candidate.py tests/test_finding_lifecycle.py tests/test_verifier.py
10 passed in 0.03s
```

The CLI exposes `finding-create` and controlled `finding-transition`.
