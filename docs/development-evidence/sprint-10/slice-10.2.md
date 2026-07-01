# Sprint 10 Slice 10.2

The ZAP contract models passive review and a limited spider as placeholders only. It declares
allowed URL, rate, spider-limit, evidence, private scope, policy, readiness, and explicit spider
approval requirements.

Active scans, destructive payloads, target expansion, unscoped spiders, and live use without
approval are denied. The contract remains network silent with a zero request budget and no live
execution.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_zap_contract.py
7 passed
```

No ZAP dependency was imported and no scan or spider ran.
