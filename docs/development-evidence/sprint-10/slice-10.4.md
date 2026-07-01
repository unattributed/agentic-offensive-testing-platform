# Sprint 10 Slice 10.4

The OSMAP contract is a clean-room, external-reference-only bridge. It accepts safe case and source
commit aliases plus a redacted, hashed, relative evidence reference. Its result states that no
code was imported, no process was invoked, no request was sent, and no live execution occurred.

Vendoring, dependency import, process invocation, secret export, implicit live execution, and
generated evidence commitment are denied. OSMAP remains a separate optional project.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_osmap_contract.py
9 passed
```

The adjacent OSMAP repository was inspected read-only for provenance and licensing. No code or
generated evidence was copied.
