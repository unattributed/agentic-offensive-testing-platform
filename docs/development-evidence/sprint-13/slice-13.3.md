# Sprint 13 Slice 13.3

Contribution policy now requires source identity, immutable version, copyright, license,
influence type, clean-room method, obligations, and a reviewer decision. Only `accepted`
provenance may merge. The pull-request checklist makes the gate visible, and the provenance
register records current external boundaries without treating metadata as legal approval.

Focused validation:

```text
python3 -m pytest -q tests/test_licensing_readiness.py -k provenance
1 passed
```

No external code or documentation prose was imported.
