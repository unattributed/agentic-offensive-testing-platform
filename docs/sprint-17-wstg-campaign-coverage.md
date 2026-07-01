# Sprint 17: WSTG Campaign Coverage Engine

Sprint 17 adds a WSTG-aligned campaign coverage engine for generating approved objectives, tracking explicit coverage dispositions, and explaining whether the agent should continue or stop.

## Scope

The sprint implements a planning and coverage layer. It does not grant execution authority by itself. Generated objectives must still be governed by the active rules of engagement, request budgets, native tool registry, and evidence classification policy.

## Delivered slices

- 17.1, version-aware WSTG strategy map with executable families.
- 17.2, campaign phases for passive, browser, auth, input, validation, and report work.
- 17.3, objective generation from scope and optional ROE.
- 17.4, explicit coverage status tracking for tested, skipped, denied, blocked, and deferred objectives.
- 17.5, authentication-boundary approval checks.
- 17.6, session-management classification and raw-value exclusion.
- 17.7, bounded error and input-boundary planning with request budgets and stop conditions.
- 17.8, browser route and form metadata mapping to WSTG categories.
- 17.9, evidence-informed next-objective choice with an explanation.
- 17.10, coverage report rendering with continue or stop reasoning.

## Safety model

The WSTG strategy map records coverage possibilities, not authority. An objective is emitted only when the phase and executable family are explicitly approved by campaign scope. When ROE is supplied, the generator also checks tool or executable family permission, risk tier, evidence classification, URL scope, host scope, and port scope.

Authentication and session objectives require explicit authenticated context and session-material approval. Session observations record cookie names and attributes only. Raw cookie values are rejected and must be handled by Sprint 16 vault mechanisms before any later authenticated execution sprint.

Input-boundary and error-handling checks are planning contracts only. They record allowed payload classes, bounded request counts, and stop conditions. State-changing input checks are denied in this sprint.

## Evidence and reporting

Coverage records must use one of the explicit dispositions:

- `tested`
- `skipped`
- `denied`
- `blocked`
- `deferred`

Tested records require evidence references. Non-tested records require reasons. The coverage report renders objective status, evidence references, and the next continue or stop decision without creating vulnerability findings.

## Validation

Focused validation:

```bash
python -m pytest -q \
  tests/test_wstg_strategy_map.py \
  tests/test_wstg_objective_generator.py \
  tests/test_wstg_coverage.py \
  tests/test_wstg_auth_boundary.py \
  tests/test_wstg_session_management.py \
  tests/test_wstg_error_input_browser.py
```

Full validation remains:

```bash
python -m compileall -q src tests
python -m pytest
bash scripts/validate-repository-safety.sh
make PYTHON="$PWD/.venv/bin/python" check
```
