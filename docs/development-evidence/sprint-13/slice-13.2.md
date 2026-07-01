# Sprint 13 Slice 13.2

The declared audit-tool group makes dependency due diligence reproducible. A generator inventories
the project, direct runtime, direct development, direct audit-tool, and transitive distributions.
Every record has installed license metadata and a conservative review status. Unknown, MPL, and
GPL-family metadata remain explicit review blockers rather than inferred approvals.

Focused validation:

```text
python3 -m pytest -q tests/test_licensing_readiness.py -k "dependency_inventory"
2 passed
python3 scripts/generate-dependency-license-inventory.py
dependency_count=69
```

The inventory is an engineering snapshot and requires legal review before distribution.
