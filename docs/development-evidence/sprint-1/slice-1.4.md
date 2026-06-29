# Slice 1.4 evidence: live operator approval

## Functional result

Live case and campaign commands now accept a separate private program profile and operator-approval record. The approval record must be approved, active, bound to the operator and authorization reference, match the SHA256 of the exact scope file, and cover the objective or campaign identifier. The explicit `--operator-approved` flag remains mandatory as a runtime confirmation.

The end-to-end CLI test writes three private synthetic documents, hashes the scope, invokes a live case, passes every policy check, and reaches the deliberately network-silent live adapter. The evidence record proves `manual_review`, `live-adapter-stub`, and zero requests.

## Validation

Command:

```bash
python3 -m pytest tests/test_config.py tests/test_policy_gate.py tests/test_cli.py tests/test_campaign_loop.py -k 'approval or live_cli or example_dry_run or campaign'
```

Result:

```text
9 passed, 25 deselected in 0.06s
```

Negative tests prove denial for a missing approval record, mismatched scope hash, unapproved objective, and expired approval. The approval example is structurally usable but intentionally denied and expired.

No external system was contacted.
