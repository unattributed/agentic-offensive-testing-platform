# Slice 1.3 evidence: rules of engagement

## Functional result

Live policy evaluation now binds the rules of engagement to the accepted program policy by SHA256. It requires a timezone-aware confirmation, acknowledged prohibited actions, confirmed evidence handling, an emergency-contact reference, instability and authentication-lockout stops, an active half-open UTC test window, mandatory campaign stop conditions, human report review, and disabled automatic submission.

The scope parser validates nested window, evidence, reporting, and rules-of-engagement structures before policy evaluation.

## Validation

Command:

```bash
python3 -m pytest tests/test_config.py tests/test_policy_gate.py -k 'rules or window or stop or report or complete_live'
```

Result:

```text
6 passed, 19 deselected in 0.04s
```

The positive live relationship remains allowed. Negative tests prove denial outside the active window, on policy-digest mismatch, with a missing authentication-lockout stop, and when automatic report submission is enabled.

No network execution occurred. All values are synthetic and reserved for tests.
