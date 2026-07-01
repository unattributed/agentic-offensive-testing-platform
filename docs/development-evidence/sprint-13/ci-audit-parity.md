# Sprint 13 CI audit parity

CI now installs the declared development and audit groups, runs the proprietary metadata audit,
generates and validates a temporary dependency license inventory, verifies that commercial release
decisions remain blocked, and audits dependencies for known vulnerabilities. Official Node 24
action majors replace the deprecated Node 20 action majors.

Local validation:

```text
python3 scripts/audit-proprietary-license.py
python3 scripts/generate-dependency-license-inventory.py --output /tmp/dependency-license-inventory.json
python3 scripts/audit-commercial-release-readiness.py
python3 -m pip_audit
```

All commands passed. No distribution or live operation occurred.
