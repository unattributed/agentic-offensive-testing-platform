# Development plan public posture addendum

This addendum updates the repository posture assumptions in `docs/development-plan.md` after AOTP was made public.

## Current repository posture

AOTP is public source-available with all rights reserved. The public repository contains framework code, tests, documentation, examples, and inert placeholder material.

Operational material remains private and untracked. This includes profiles, scopes, targets, accounts, authorization records, correspondence, generated evidence, screenshots, reports, findings, traces, campaign memory, and private assessment material.

## Development-plan interpretation

Where `docs/development-plan.md` says the repository is private, read that as historical Sprint 0 context unless the statement is about private operational material.

Where `docs/development-plan.md` says private profiles, private scopes, private evidence, or private campaign memory, that language remains current and authoritative.

Where Sprint 13 says public release review is future work, public visibility has already occurred, so the immediate public-release risk review is now tracked in `docs/public-release-risk-review.md`.

## Immediate inserted slice

Sprint 4.0 is inserted before Sprint 4.1.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 4.0 public repository posture alignment | Align README, license, contribution, licensing, commercialization, and public-risk docs with public source-available visibility | Public-facing docs no longer claim the repository is private; private operational material remains prohibited | `./scripts/validate-repository-safety.sh` and documentation review | reviewed diff and public-risk review | README, LICENSE, contribution, licensing, commercialization, public-risk docs | `align public repository posture` |

Sprint 4.0 acceptance:

- Repository visibility is public.
- License posture is source-available and all rights reserved.
- README states public code and private operations.
- CONTRIBUTING states external contributions require owner authorization.
- Public security reporting warns against public disclosure of sensitive material.
- Public release risk review exists.
- No private scope, target, credential, screenshot, finding, report, trace, generated capture, or real evidence is committed.

## Sprint 4 continuation rule

After Sprint 4.0, continue Sprint 4.1 through Sprint 4.6 as planned. WSTG cases and adapter contracts must remain dry-run safe and network-silent by default.

## Future Sprint 13 interpretation

Sprint 13 should now focus on licensing and commercialization readiness for a public source-available project, not on whether a public release may happen. It should still include recurring public-release risk review, dependency license inventory, provenance controls, contribution controls, and legal review before any broader license or commercial distribution change.
