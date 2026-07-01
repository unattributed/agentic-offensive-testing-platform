# Sprint 0 Slice 0.2

Initial commit `094e756` added the repository safety validator, ignore rules, and negative safety
tests. Later hardening expanded archive-mode exclusions and reachable-history auditing.

Current focused validation:

```text
python3 -m pytest -q tests/test_repository_safety.py
2 passed
./scripts/validate-repository-safety.sh
repository safety validation passed
```

The negative fixture proves secret-like content outside excluded generated paths fails closed.
