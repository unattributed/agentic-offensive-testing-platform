# Sprint 5 Slice 5.6: evidence-bound report mapping and closeout

## Implemented behavior

Panel report review is represented by a local decision record containing the exact evidence
manifest SHA256, reviewer alias, decision, timestamp, and rationale. Finding candidates retain the
review record path and SHA256.

At report generation, the reporter matches every candidate to a manifest in the report set,
re-derives whether panel review is required, validates the review record, and refuses candidate
controlled attempts to disable the gate.

The evidence appendix reads only the integrity-verified `panel-evidence.json` artifact and renders
the captured panel alias, panel type, planned observations, network-silent status, request count,
and evidence inclusion status. It does not infer vulnerability, impact, or remediation fields.

## Adversarial regressions

- A service control panel objective cannot bypass policy by claiming a web category.
- An action cannot be both approved and denied in panel scope.
- A configured panel denial cannot be ignored.
- An empty observation request is denied before evidence construction.
- A forged panel candidate with `report_review_required: false` remains excluded.
- A panel campaign cannot omit its lockout-risk stop condition.

## Validation

- Focused Sprint 5 tests.
- Full project test suite and compile gate: 178 tests passed.
- Repository safety validation passed.
- CLI panel campaign, evidence verification, report review, candidate lifecycle, and report checks.

## Sprint acceptance

Unscoped panels and credential attacks are refused, lockout risk pauses before execution, dry-run
panel evidence is network-silent and integrity-verified, and reports remain evidence-bound.
