# Sprint 9 development evidence

Sprint 9 implements bounded local structured model assistance without granting authority or
exposing secrets.

| Slice | Topic | Commit | Status |
|---|---|---|---|
| 9.1 | Loopback configuration and model allowlist | `1c194bf` | Complete |
| 9.2 | Structured JSON adapter and bounded failures | `ba509f2` | Complete |
| 9.3 | Approved-objective planner schema | `40c9299` | Complete |
| 9.4 | Evidence-only verifier and report assistance | `e2d5a3a` | Complete |
| 9.5 | Recursive prompt secret stripping | `84f1f6c` | Complete |
| 9.6 | Adversarial no-secret regression tests | `d47efef` | Complete |

Acceptance proof:

- loopback endpoints, approved models, structured output, and bounded timeouts are mandatory;
- planning suggestions cannot add objectives or authorize actions;
- verification and report assistance cannot set authoritative fields or invent evidence;
- secrets do not reach serialized prompts and secret-bearing output fails closed;
- invalid or unavailable local model behavior produces bounded errors; and
- all tests use injected in-memory transports, with no model service or target contacted.

Validation: 75 focused tests and 292 full project tests passed in the repository virtual
environment. Compile and repository safety gates passed. The system Python lacks `pytest`, so
unmodified `make check` cannot complete its test phase; `make PYTHON=.venv/bin/python check`
passed.

Timestamped closeout evidence:
[`closeout-20260630T224957Z`](closeout-20260630T224957Z/README.md).
The local evidence archive is
`.aotp/evidence/development/sprint-9/closeout-20260630T224957Z.tar.gz` with SHA256
`eb8dd5749651c393bac4ccf84c4a3c2bafbc2d4512556dadbeaa9c23302cedf4`.
