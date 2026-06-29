# Slice 1.2 evidence: live authorization metadata

## Functional result

The policy gate now validates a real relationship between two separate private documents: campaign scope and program profile. Live authorization requires a supported authorization type, non-placeholder references, timezone-aware issuance and validity timestamps, an active validity interval, matching program and authorization references, an accepted policy date, program-approved asset and testing category, non-prohibited action, and a scope rate no higher than the program ceiling.

Targets also enforce explicitly listed environments and approved test-account aliases.

## Validation

Command:

```bash
python3 -m pytest tests/test_config.py tests/test_policy_gate.py -k 'live or authorization or profile or environment or account'
```

Result:

```text
10 passed, 11 deselected in 0.04s
```

The positive test passes a complete synthetic authorization relationship. Negative tests prove denial for an absent private profile, mismatched profile alias, mismatched authorization reference, expired authorization, out-of-scope asset, forbidden category, excessive rate limit, unlisted environment, and unapproved account.

The fixtures use reserved aliases and no live target or program data.
