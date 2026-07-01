# Contributing

This repository is public source-available, but external contributions are not accepted by
default. Repository-owner authorization is required before development begins.

By contributing, you confirm that the work is original or that every external influence has a
complete provenance record under the
[third-party attribution policy](docs/third-party-attribution-policy.md). Unclear provenance,
unknown licensing, or unreviewed copied material blocks merge.

## Change process

1. Keep changes small and map them to a development-plan slice.
2. Add negative tests for every authorization or policy boundary.
3. Use aliases and reserved placeholder domains only.
4. Never commit real profiles, scopes, targets, accounts, secrets, correspondence, evidence,
   screenshots, findings, reports, traces, generated captures, or campaign memory.
5. Record each dependency and external source in the license inventory and provenance register.
6. Complete the pull-request provenance checklist.
7. Run `make check` before review.
8. Require human review for live execution, redaction, policy, evidence, and reporting changes.
9. Do not open public issues or pull requests containing private assessment material.

## Provenance decision

Every contribution must be classified as one of:

- `original`: independently authored for this repository.
- `external_reference_only`: public interfaces or behavior were consulted, with no copied
  implementation.
- `clean_room_reimplementation`: requirements and interfaces were recorded separately from an
  independently authored implementation.
- `third_party_included`: code or content is proposed for inclusion with exact source, version,
  copyright, license, and redistribution analysis.

Only a provenance decision of `accepted` permits merge. `legal_review_required`, `rejected`, or
missing records block merge.

Do not vendor code from OSMAP, `ai-browser-security-test-suite`, or any other project without
explicit provenance and licensing review. Prefer clean-room adapter contracts and external process
boundaries.
