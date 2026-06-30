# Sprint 5 Slice 5.2: safe panel observations

## Outcome

Slice 5.2 adds a deterministic, network-silent service control panel observation planner. It models safe observation categories only and records dry-run evidence metadata without sending traffic, submitting credentials, crawling, mutating state, or making vulnerability claims.

## Implemented behavior

- Adds explicit safe panel observation identifiers:
  - `response_header_metadata`
  - `tls_configuration_metadata`
  - `login_exposure_metadata`
  - `version_banner_metadata`
  - `default_page_metadata`
  - `indexing_metadata`
- Adds `build_panel_dry_run_observation_plan()` for deterministic placeholder evidence metadata.
- Extends the policy gate to deny panel actions that are not explicitly approved by the scoped panel alias.
- Extends the policy gate to deny requested panel observations that are not approved as safe.
- Adds a safe observation dry-run case fixture.
- Updates the panel dry-run scope fixture to approve only the new safe observation planning action.
- Keeps dry-run execution network-silent with `request_count` equal to `0`.

## Safety boundary

No login attempts, credential guessing, default-password checks, brute force, credential stuffing, password spraying, token replay, session hijacking, lockout-triggering behavior, destructive actions, unsafe crawling, real panel URLs, screenshots, captures, credentials, private target material, or live network activity were introduced.

## Validation

The runner captures focused and full validation output for:

- `python -m pytest tests/test_control_panel_safe_observations.py`
- `python -m pytest tests/test_control_panel_targets.py`
- `make PYTHON=.venv/bin/python compile`
- `make PYTHON=.venv/bin/python test`
- `make PYTHON=.venv/bin/python check`
- `./scripts/validate-repository-safety.sh`
- CLI policy-check allowed fixture
- CLI policy-check unsupported observation denial fixture
- CLI run-case dry-run fixture
- Evidence verification

## No private material

No private scope, target, credential, screenshot, finding, report, trace, generated capture, campaign memory, or real evidence was committed.

## Deferred

Sprint 5.3 should map panel-specific dry-run observation metadata into richer evidence objects while preserving the current policy denials and network-silent default.
