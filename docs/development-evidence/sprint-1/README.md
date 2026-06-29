# Sprint 1 closeout evidence

Sprint 1 delivers executable scope, authorization, rules-of-engagement, approval, and preflight policy behavior. It does not claim that live testing adapters are implemented. A policy-approved live case reaches a network-silent `manual_review` stub with zero requests.

## Slice commits

| Slice | Commit | Functional evidence |
|---|---|---|
| 1.1 private scope model | `130dce7` | Typed scope and program-profile parsing with nested target, environment, account, category, limit, and evidence validation |
| 1.2 authorization metadata | `1f6ac6e` | Positive live authorization relationship plus expiry, alias, asset, category, action, and rate denials |
| 1.3 rules of engagement | `988b692` | Policy digest binding, active UTC window, required stops, evidence acknowledgement, and manual-only reporting |
| 1.4 operator approvals | `03d0c68` | Private approval record bound to scope hash, operator, authorization, validity, objective or campaign, and explicit runtime confirmation |
| 1.5 fail-closed coverage | `56253c2` | Exact domain and wildcard boundaries plus non-executing structured `policy-check` |
| External template control | `36deedf` | Local provenance and hash gate for pinned YAML and YARA sources without downloading or executing them |

Each slice has its own evidence record in this directory.

## Full validation

Command:

```bash
make check
```

Result:

```text
python3 -m compileall -q src tests
python3 -m pytest
66 passed in 0.18s
./scripts/validate-repository-safety.sh
repository safety validation passed
```

Functional smoke commands also proved:

- example configuration validation returns `allowed`;
- dry-run case policy preflight returns `allowed` with no reasons;
- the example web campaign completes with structured state and evidence;
- evidence verification passes; and
- the example Nuclei source is denied because it is disabled, unreviewed, and absent.

## Sprint acceptance

- The example configuration cannot authorize live use.
- A complete synthetic private scope, program profile, and approval record can pass live policy checks.
- Authorization expiry, target expansion, policy mismatch, forbidden actions, unsafe rate limits, inactive windows, missing approvals, confidentiality gaps, and reporting automation fail closed.
- The policy decision can be inspected before execution.
- No test or quick-start command contacts a target.
- No real program, target, account, secret, or evidence is committed.
