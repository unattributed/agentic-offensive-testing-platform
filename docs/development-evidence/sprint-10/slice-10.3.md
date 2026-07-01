# Sprint 10 Slice 10.3

The mitmproxy contract models authorized local capture placeholders only. It declares proxy
context, rate, evidence, private scope, policy, readiness, and local capture authorization
requirements.

Redaction and credential stripping are mandatory. Private CA material, credentials, transparent or
unscoped interception, target expansion, and unapproved live use are denied. The contract remains
network silent with a zero request budget and no live execution.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_mitmproxy_contract.py
7 passed
```

No mitmproxy dependency was imported and no traffic was intercepted.
