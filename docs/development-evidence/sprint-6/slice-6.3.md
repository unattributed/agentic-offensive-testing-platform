# Sprint 6 Slice 6.3: endpoint and request budgets

Each fuzzing objective maps endpoint aliases to planned request counts. Policy rejects
per-endpoint or total overruns. `FuzzingRequestBudget` refuses counter reservations beyond either
limit, and campaign state persists per-endpoint counters. Network-silent dry runs retain zero
actual requests.

Focused validation is in `tests/test_bounded_fuzzing.py`.
