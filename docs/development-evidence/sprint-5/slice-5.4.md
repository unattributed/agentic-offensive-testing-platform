# Sprint 5 Slice 5.4: report review gating

## Implemented behavior

This slice adds report-review gating for service control panel evidence records.
Panel evidence remains excluded by default and cannot become a finding candidate
until a named human reviewer explicitly marks the evidence as reviewed for candidate creation.

## Safety properties

- No live testing is introduced.
- No login attempts are introduced.
- No credential guessing or default-password checks are introduced.
- No brute force, crawling, token replay, session hijacking, or destructive panel actions are introduced.
- Panel evidence stays excluded pending review by default.
- Report generation includes only integrity-verified evidence and report-ready candidates.
- Panel candidates require named human review before candidate creation.
- Panel candidates still require human validation before report-ready state.

## Code changes

- `src/aotp/report_review.py`: report-review gate helpers for panel evidence.
- `src/aotp/finding_candidate.py`: candidate creation now enforces panel evidence review gating.
- `src/aotp/reporter.py`: report generation checks report-review inclusion status.
- `src/aotp/cli.py`: `finding-create` accepts explicit report-review flags.
- `src/aotp/capability_registry.py`: module summary records report-review gating.
- `tests/test_report_review_gating.py`: focused tests for gating behavior.

## Validation

Validation is performed by the local runner using focused tests, full test suite,
compile checks, repository safety checks, CLI policy checks, dry-run evidence generation,
finding candidate denial, reviewed candidate creation, lifecycle transition, report generation,
evidence verification, and PR creation.

## Known limitations

This slice gates panel evidence promotion and report inclusion only. It does not
create live panel checks, vulnerability claims, automatic report submissions, or
exploitability assessments.
