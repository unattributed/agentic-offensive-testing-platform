# Slice 2.3 evidence: checkpointed campaign loop

## Functional result

The deterministic loop now checkpoints before and after each objective, uses stable iteration-derived run identifiers, writes evidence before advancing state, and can continue from a loaded checkpoint without repeating completed objectives or replacing their evidence.

Resume revalidates the exact scope-file hash, campaign-definition hash, state status, and objective membership. Policy denial produces a stopped-by-policy evidence manifest and state disposition.

## Validation

```bash
python3 -m pytest tests/test_campaign_loop.py tests/test_campaign_state.py tests/test_cli.py
```

```text
12 passed in 0.09s
```

Tests execute one objective, reload the on-disk checkpoint, finish the second objective, and prove the first evidence file is unchanged. A changed scope file is rejected before resume.
