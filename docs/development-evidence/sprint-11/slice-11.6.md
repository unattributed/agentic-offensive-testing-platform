# Sprint 11 Slice 11.6

The v0.1 release checker verifies project version, required documentation, license and security
files, imports, compile, tests, repository safety, reachable history, evaluator demo output, and
the deterministic placeholder report.

The checklist is complete for a demonstration release candidate. It does not create a package,
tag, live adapter, private operation, or publication.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_release_check.py
3 passed
```

The full release command and results are captured in Sprint 11 closeout evidence.
