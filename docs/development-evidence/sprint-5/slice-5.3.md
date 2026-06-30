# Sprint 5 Slice 5.3, panel evidence records

## Purpose

Slice 5.3 maps deterministic safe panel observation plans into local evidence artifacts.
It keeps the service control panel module dry-run only and creates no findings or report-ready claims.

## Implemented behavior

- Added `src/aotp/panel_evidence.py` for panel-specific evidence record construction, validation, and atomic writing.
- Added `cases/control-panel-evidence-records.example.yaml` as a public-safe dry-run case fixture.
- Updated `src/aotp/cli.py` so safe panel observation runs write `panel-evidence.json` and register it in the evidence manifest.
- Added focused tests for record validation, manifest registration, CLI evidence writing, and evidence verification.
- Updated the service control panel capability summary to identify the panel evidence artifact.

## Safety boundary

- No login attempts.
- No credential guessing.
- No default-password checks.
- No brute force.
- No credential stuffing.
- No password spraying.
- No token replay.
- No session hijacking.
- No lockout-triggering checks.
- No destructive panel actions.
- No unsafe panel crawling.
- No real panel URLs, screenshots, captures, credentials, or private target material.
- Dry-run execution remains network-silent with zero requests.
- Panel evidence records are excluded pending human review and cannot contain finding claims.

## Validation

Local runner validation for this slice must include:

- `python -m pytest tests/test_panel_evidence_records.py`
- `python -m pytest tests/test_control_panel_safe_observations.py`
- `make PYTHON=.venv/bin/python compile`
- `make PYTHON=.venv/bin/python test`
- `make PYTHON=.venv/bin/python check`
- `./scripts/validate-repository-safety.sh`
- CLI `policy-check` for the panel evidence fixture
- CLI `run-case --dry-run` for the panel evidence fixture
- CLI `evidence-verify` for `.aotp/evidence`

## No private material

No private scope, target, credential, screenshot, finding, report, trace, generated capture,
campaign memory, or real evidence was committed.

## Deferred work

Slice 5.4 should add report-review gating for panel evidence so generated records remain excluded
until a human reviewer explicitly promotes a finding candidate.
