# Dependency license inventory

This inventory is a review aid, not legal advice.

| Dependency | Purpose | Direct | Version policy | License status | Review action |
|---|---|---:|---|---|---|
| Python | Runtime | yes | 3.11 or newer | PSF license, verify distribution | record deployed runtime |
| PyYAML | YAML parsing | yes | `>=6.0,<7` | MIT, verify installed metadata | review notices before distribution |
| pytest | Development tests | dev only | `>=8.0,<9` | MIT, verify installed metadata | exclude from runtime package |

CI actions are build tooling and must also be reviewed before commercial distribution. Add every future adapter dependency before merge and capture its source, version, SPDX expression, transitive obligations, and redistribution decision.
