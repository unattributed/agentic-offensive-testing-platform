# Sprint 6 Slice 6.2: payload budgets

Fuzzing scope now names approved safe payload classes and a positive payload ceiling. Objectives
name payload classes and a payload count without embedding payload values. Missing, zero, unsafe,
or over-budget values are denied before execution.

Focused validation is in `tests/test_bounded_fuzzing.py`.
