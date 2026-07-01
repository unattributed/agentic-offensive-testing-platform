# Sprint 12 Slice 12.1

Program profiles now carry a required profile identifier and private data classification. The
profile remains a policy document separate from technical scope, and live policy evaluation
continues to deny a missing profile. Private profile naming patterns and directories are ignored.

Focused validation:

```text
python3 -m pytest -q tests/test_config.py tests/test_policy_gate.py -k "program_profile or profile"
5 passed
```

Only the synthetic example profile is tracked. No private program terms or target data were added.
