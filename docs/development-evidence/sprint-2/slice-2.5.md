# Slice 2.5 evidence: pause, reviewed resume, and stop

## Functional result

A human-gated objective now pauses before execution with zero-request evidence. Resume requires a private review decision bound to the exact checkpoint SHA256, campaign, objective, operator, timestamp, and decision.

Approval marks a pre-execution objective as reviewed and continues the campaign. Post-execution approval completes the reviewed objective. Denial stops by condition. An explicit stop persists `stopped_by_operator`. The CLI now performs the complete reviewed resume rather than only changing a status string.

## Validation

```bash
python3 -m pytest tests/test_campaign_control.py tests/test_campaign_loop.py tests/test_campaign_state.py tests/test_cli.py tests/test_config.py
```

```text
25 passed in 0.14s
```

Tests prove pre-execution pause, checkpoint-bound approval, continued execution to completion, mismatched checkpoint rejection, review denial, persistent operator stop, and end-to-end CLI resume.
