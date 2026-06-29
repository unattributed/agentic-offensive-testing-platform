# Slice 1.1 evidence: private scope model

## Functional result

`parse_scope` now returns a typed scope containing program, sponsor, operator, target, environment, approved-account, category, forbidden-action, rate-limit, and evidence boundaries. `parse_program_profile` independently validates program policy context. Unknown fields, duplicate target aliases, contradictory asset lists, malformed nested values, and unsupported schema versions fail closed.

The committed example is dry-run only and uses reserved placeholders.

## Validation

Command:

```bash
python3 -m pytest tests/test_config.py tests/test_policy_gate.py
```

Result:

```text
15 passed in 0.04s
```

The tests parse both example models, resolve an approved target and provisioned account alias, and prove rejection of unknown fields, duplicate aliases, contradictory in-scope and out-of-scope declarations, missing scope, target expansion, forbidden actions, unapproved fuzzing, unlisted services and APIs, escaped evidence paths, absent human approval, and failed redaction.

No private profile, target, account, secret, or assessment evidence was used or committed.
