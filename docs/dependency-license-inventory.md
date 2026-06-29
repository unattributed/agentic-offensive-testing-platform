# Dependency license inventory

This inventory is a review aid, not legal advice.

| Dependency | Purpose | Direct | Version policy | License status | Review action |
|---|---|---:|---|---|---|
| Python | Runtime | yes | 3.11 or newer | PSF license, verify distribution | record deployed runtime |
| PyYAML | YAML parsing | yes | `>=6.0,<7` | MIT, verify installed metadata | review notices before distribution |
| pytest | Development tests | dev only | `>=8.0,<9` | MIT, verify installed metadata | exclude from runtime package |
| LangGraph | Planned durable campaign orchestration | no, prospective | not yet pinned | MIT in upstream repository, reverify before adoption | prototype in Sprint 2.7 and inventory transitives |
| Nuclei templates | Optional external YAML source | no, not vendored | exact commit and bundle hash required | MIT repository, template behavior requires individual review | keep external, signed, allowlisted, and policy-gated |
| YARA | Optional provided-artifact classifier | no, prospective | not yet pinned | BSD-3-Clause engine, rules retain their own licenses | review engine and each ruleset separately |
| Yara-Rules community rules | Potential external rules | rejected for vendoring | not applicable | GPL-2.0 ruleset | do not include in proprietary distribution |

CI actions are build tooling and must also be reviewed before commercial distribution. Add every future adapter dependency before merge and capture its source, version, SPDX expression, transitive obligations, and redistribution decision.
