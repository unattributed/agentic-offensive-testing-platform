# Dependency license inventory

This is an engineering metadata inventory, not legal advice or a distribution approval.

The machine-readable
[`dependency-license-inventory.json`](dependency-license-inventory.json) records every installed
Python distribution in the validated project audit environment. Each record includes its exact
version, dependency type, installed license metadata, source metadata, and a conservative review
status. Unknown metadata is never treated as approval.

## Declared dependencies and tools

| Dependency | Type | Version policy | Installed license metadata | Distribution posture |
|---|---|---|---|---|
| PyYAML | runtime | `>=6.0,<7` | MIT | Pending legal review |
| LangGraph | runtime | `>=1.2.7,<1.3` | MIT | Pending legal review |
| LangGraph SQLite checkpoint | runtime | `>=3.1,<3.2` | MIT | Pending legal review |
| build | development | `>=1.5,<2` | MIT | Development and package build only |
| pytest | development | `>=9.0.3,<10` | MIT | Test environment only |
| pip-audit | audit tooling | `>=2.10,<3` | Apache-2.0 classifier | Audit environment only |
| pip-licenses | audit tooling | `>=5.5,<6` | MIT | Audit environment only |
| ShellCheck | external audit tooling | system package | GPL-3.0-or-later | Never bundled or linked |
| actions/checkout | CI tooling | commit `de0fac2e` (`v6.0.2`) | MIT | Remote CI action only |
| actions/setup-python | CI tooling | commit `a309ff8b` (`v6.2.0`) | MIT | Remote CI action only |

Python itself and the operating-system distribution require separate deployment review. Workflow
actions are pinned remote build tooling and are not shipped in the Python package.

## Review status meanings

- `owner_controlled_proprietary`: this project and its all-rights-reserved license.
- `metadata_recorded_pending_legal_review`: permissive-looking installed metadata was recorded but
  is not a legal approval.
- `notice_and_file_scope_review`: installed metadata includes MPL terms that require notice and
  file-scope analysis before distribution.
- `distribution_blocked_pending_legal_review`: installed metadata includes a GPL-family term.
- `manual_metadata_review_required`: installed metadata was missing or ambiguous.

The inventory includes transitive packages introduced by runtime, development, and audit roots.
Before distribution, legal review must confirm upstream license texts, notices, source terms,
trademarks, and whether each dependency is shipped, linked, invoked externally, or excluded.

Optional template ecosystems and external adapters remain unvendored. Their repositories, rule
sets, and data files retain separate licenses and require source-specific review before use.
