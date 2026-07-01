# Sprint 13 Slice 13.1

Package metadata now declares `LicenseRef-Proprietary` and includes `LICENSE.md` using PEP 639
fields. The build backend minimum supports those fields. A repository audit rejects missing
all-rights-reserved statements and any open-source license classifier.

Focused validation:

```text
python3 -m pytest -q tests/test_licensing_readiness.py
2 passed
python3 scripts/audit-proprietary-license.py
proprietary license audit passed
```

This is an engineering metadata check, not legal advice.
