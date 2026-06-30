# Slice 2.4 evidence: scheduler and safety budgets

## Functional result

The scheduler now honors objective dependencies before priority and remains deterministic for ties. Every objective declares a non-negative request budget.

The safety budget rejects work before execution when iteration, runtime, total-request, per-minute, or consecutive-failure limits are exhausted. A pre-execution budget denial writes zero-request evidence, a stop event, and a stopped objective disposition.

## Validation

```bash
python3 -m pytest tests/test_campaign.py tests/test_campaign_loop.py tests/test_safety_budget.py tests/test_scheduler.py tests/test_campaign_state.py
```

```text
24 passed in 0.08s
```

Tests cover dependency ordering, deterministic ties, cycle rejection, predictive request denial, rate-window reset, failure limits, negative counters, and an end-to-end request-limit stop with evidence proving no request was executed.
