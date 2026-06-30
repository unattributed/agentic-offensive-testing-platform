# Sprint 6 Slice 6.1: fuzzing authorization

## Implemented behavior

Bounded fuzzing now requires all of the following before policy allows an objective:

- the `bounded_fuzzing` category is allowlisted;
- fuzzing is explicitly authorized in scope;
- every requested fuzzing action is explicitly approved;
- no requested action is explicitly denied;
- state-changing fuzzing has separate authorization;
- positive payload, request, endpoint, and runtime budgets are present.

Scope parsing rejects unknown approved actions, contradictory approved and denied actions,
missing mandatory safety denials, approvals while fuzzing is disabled, and state-changing
authorization without base fuzzing authorization.

## Validation

- `python -m pytest tests/test_fuzzing_authorization.py`
- focused result: 7 tests passed
- full result: 185 tests passed
- compile and repository safety gates passed

## Safety boundary

No fuzzing execution, payload generation, corpus ingestion, target expansion, or network activity
is introduced by this slice.
