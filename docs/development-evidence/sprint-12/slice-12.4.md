# Sprint 12 Slice 12.4

Private campaign memory now validates alias-only identifiers, ISO dates, SHA256 evidence and
finding fingerprints, enumerated outcomes, and duplicate status. Exact fingerprints are compared
only within the same asset alias and test type. Files are atomic, mode `0600`, redaction-checked,
and covered by the repository ignore policy.

Focused validation:

```text
python3 -m pytest -q tests/test_campaign_memory.py
7 passed
```

The tests use synthetic aliases and hashes. No target data or finding prose was stored.
