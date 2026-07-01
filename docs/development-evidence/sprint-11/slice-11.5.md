# Sprint 11 Slice 11.5

The release audit runs the current-tree safety validator, inventories tracked and historical paths,
rejects tracked symlinks, and scans every reachable commit for prohibited path classes and likely
secret patterns.

Regression tests prove safe history passes, a deleted historical secret still fails, and execution
outside a Git worktree is refused.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_repository_release_audit.py
3 passed
```

The repository audit record is captured in `docs/repository-safety-review-v0.1.md`.
