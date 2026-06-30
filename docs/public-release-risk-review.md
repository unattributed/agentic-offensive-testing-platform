# Public release risk review

## Current status

AOTP is public source-available with all rights reserved. The public repository contains framework code, policy logic, documentation, examples, tests, and inert placeholder material. Operational profiles, scopes, targets, credentials, correspondence, findings, reports, screenshots, traces, generated captures, campaign memory, and real assessment evidence must remain outside the repository.

## Release decision

Public visibility is acceptable only for source review, portfolio review, and evaluator discussion. Public visibility does not authorize operational use, redistribution, sublicensing, or live testing.

The current license remains all rights reserved. No open-source license is granted.

## Public-risk controls

- Example scopes remain dry-run safe.
- Live testing requires private untracked program profiles, private scopes, explicit authorization references, rules-of-engagement confirmation, allowed windows, rate limits, evidence rules, disclosure rules, stop conditions, and operator approval.
- The policy gate remains authoritative before execution.
- Initial live adapters remain network-silent stubs.
- AOTP has no automatic report submission adapter.
- Generated state and evidence remain under ignored paths.
- Repository safety validation blocks common private evidence paths and common secret forms.
- Security reports that include sensitive material must use private channels.

## Public repository review checklist

| Area | Status | Notes |
|---|---|---|
| Repository visibility | public | Confirmed by repository metadata. |
| License posture | source-available, all rights reserved | `LICENSE.md` states no open-source grant. |
| README posture | aligned | README describes public code and private operations. |
| Contribution posture | aligned | External contributions require owner authorization. |
| Security reporting | aligned | Sensitive reports must not be public issues. |
| Private material policy | aligned | Real targets, findings, screenshots, and evidence are prohibited. |
| Evidence paths | aligned | `.aotp/`, evidence, reports, screenshots, traces, private files, keys, and HAR files are ignored. |
| Reference project boundary | aligned | OSMAP and browser-suite integrations use clean-room contracts only. |
| Live adapter posture | aligned | Live adapters are not enabled by default. |
| Commercial posture | pending | Commercial path remains undecided and requires legal review. |

## Required recurring checks

Before every public-facing sprint closeout, run and record:

```bash
python3 -m compileall src tests
python3 -m pytest
./scripts/validate-repository-safety.sh
make test
```

Before every merge, review:

```bash
git status --short
git diff --cached --stat
git diff --cached
```

Search for private or stale posture language:

```bash
rg -n "private repository|repository remains private|private proprietary|open-source license is granted|real target|credential|cookie|token|screenshot|proxy capture|finding" .
```

Review results manually because the safety validator is a coarse defense, not a substitute for human review.

## Known limitations

- This document is an engineering risk review, not legal advice.
- Git history has not been deeply rewritten or independently audited in this document.
- Dependency license inventory remains an engineering review aid and requires legal review before commercial distribution.
- Public repository visibility increases the importance of private operational hygiene, issue triage, and contribution controls.

## Sprint 4.0 closeout note

Sprint 4.0 exists to align repository language with the current public visibility before Sprint 4 continues. Sprint 4.1 and later must continue to treat operational material as private and must not introduce live network behavior by default.
