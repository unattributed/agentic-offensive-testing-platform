# Sprint 12 Slice 12.3

Live policy evaluation now compares the entire technical scope with the private program profile,
not only the current objective. Any configured out-of-scope or unapproved alias, forbidden or
unapproved testing category, or omitted program prohibition denies execution.

Focused validation:

```text
python3 -m pytest -q tests/test_policy_gate.py -k "profile_boundaries or out_of_scope"
2 passed
```

The denial matrix uses aliases only. No live target or private program data was used.
