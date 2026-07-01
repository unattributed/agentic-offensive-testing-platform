# Public release risk review

This is an engineering risk review, not legal advice.

## Current posture

Repository metadata was observed as `PUBLIC` on 2026-07-01. The source remains proprietary and
all rights reserved. Public visibility permits source review only under the repository terms; it
does not create an open-source grant, commercial distribution approval, evaluator license, or
operational authorization.

Real operational material remains private and prohibited from the repository. This includes
profiles, scopes, targets, accounts, credentials, correspondence, evidence, screenshots, findings,
reports, traces, captures, and campaign memory.

## Decisions

| Decision scope | Status |
|---|---|
| Existing source visibility for review | Current public posture |
| Commercial distribution | Blocked |
| Open-source licensing release | Blocked |
| Evaluator distribution | Blocked |
| Operational material release | Prohibited |

The machine-readable
[`public-release-risk-review.yaml`](public-release-risk-review.yaml) records each blocker, evidence
reference, and required action. No release decision may be inferred from repository visibility or
passing engineering tests.

## Controls verified

- Package metadata declares `LicenseRef-Proprietary` and includes `LICENSE.md`.
- Repository safety validation rejects common private paths and secret forms.
- Reachable history is audited for prohibited paths and secret patterns.
- Example scopes and campaigns remain placeholders and network-silent.
- Live execution remains separately authorized and policy-gated.
- Report packages remain drafts until named-human review.
- No automatic submission transport exists.
- Dependency metadata and conservative review statuses are tracked.
- External influences require provenance and an accepted merge decision.
- Commercialization and evaluator distribution remain explicitly blocked.

## Blocking conditions

Legal terms, dependency obligations, unresolved provenance, evaluator terms, commercialization
items, and release artifacts are not approved. Counsel and accountable owner roles must close
their items with current evidence. An engineering test or source audit cannot close those reviews.

## Required recurring validation

```bash
python3 scripts/audit-proprietary-license.py
python3 scripts/generate-dependency-license-inventory.py
python3 scripts/audit-commercial-release-readiness.py
python3 -m compileall -q src tests scripts
python3 -m pytest
./scripts/validate-repository-safety.sh
./scripts/audit-repository-release.sh
make check
```

The review must be updated when visibility, licensing, dependencies, external sources, release
contents, operational behavior, or commercial plans change.
