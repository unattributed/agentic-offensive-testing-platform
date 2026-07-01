# Dependency license inventory

This inventory is a review aid, not legal advice.

| Dependency | Purpose | Direct | Version policy | License status | Review action |
|---|---|---:|---|---|---|
| Python | Runtime | yes | 3.11 or newer | PSF license, verify distribution | record deployed runtime |
| PyYAML | YAML parsing | yes | `>=6.0,<7` | MIT, verify installed metadata | review notices before distribution |
| pytest | Development tests | dev only | `>=8.0,<9` | MIT, verify installed metadata | exclude from runtime package |
| LangGraph | Durable campaign orchestration | yes | `>=1.2.7,<1.3` | MIT upstream, verified for Sprint 2 | maintain parity tests and inventory transitives |
| LangGraph SQLite checkpoint | Local durable graph state | yes | `>=3.1,<3.2` | MIT upstream, verified for Sprint 2 | keep database private and review transitive SQLite components |
| Nuclei templates | Optional external YAML source | no, not vendored | exact commit and bundle hash required | MIT repository, template behavior requires individual review | keep external, signed, allowlisted, and policy-gated |
| YARA | Optional provided-artifact classifier | no, prospective | not yet pinned | BSD-3-Clause engine, rules retain their own licenses | review engine and each ruleset separately |
| Yara-Rules community rules | Potential external rules | rejected for vendoring | not applicable | GPL-2.0 ruleset | do not include in proprietary distribution |
| ai-browser-security-test-suite | External browser evidence references only | no, not imported or vendored | reviewed source commit alias required | source project declares AGPL-3.0-or-later | keep separate and require license review before any dependency or code reuse |

CI actions are build tooling and must also be reviewed before commercial distribution. Add every future adapter dependency before merge and capture its source, version, SPDX expression, transitive obligations, and redistribution decision.

## Sprint 2 LangGraph environment snapshot

The validated environment contained the following orchestration packages. This records package metadata for engineering review and is not a substitute for legal review.

| Package | Validated version | Metadata license |
|---|---:|---|
| langgraph | 1.2.7 | MIT |
| langgraph-checkpoint-sqlite | 3.1.0 | MIT |
| langchain-core | 1.4.8 | MIT |
| langgraph-checkpoint | 4.1.1 | MIT |
| langgraph-prebuilt | 1.1.0 | MIT |
| langgraph-sdk | 0.4.2 | MIT |
| pydantic | 2.13.4 | MIT |
| xxhash | 3.8.0 | BSD-2-Clause |
| aiosqlite | 0.22.1 | package metadata did not state a license; manual review required |
| sqlite-vec | 0.1.9 | metadata states MIT and Apache-2.0 |
| langsmith | 0.9.3 | MIT; installed transitively but no tracing or remote service is enabled |
