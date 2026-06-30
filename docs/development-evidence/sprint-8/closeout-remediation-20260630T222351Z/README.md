# Sprint 8 closeout remediation evidence

Timestamp: `2026-06-30T22:23:51Z`

## Finding verification

1. Proven. The combined SBOM and crypto campaign authorized crypto review but omitted all required
   crypto evidence fields. Authorized execution raised `ValueError: TLS evidence is missing`.
2. Proven. The policy gate checked crypto authorization and action only. Required evidence was
   validated later by the executor.
3. Proven. The non-git safety scan excluded only `.git` and `.venv`, so generated cache files were
   included in secret-pattern scans.

## Remediation proof

- The combined campaign now supplies metadata-only TLS, cookie, token, weak-indicator, and
  key-management evidence and completes with zero requests.
- The policy gate now rejects incomplete metadata, unsafe paths, secret-bearing fields, private
  material, extraction, brute force, decryption, replay, destructive actions, and live probing
  before execution.
- The non-git safety scan prunes `.pytest_cache`, `__pycache__`, `.venv`, `build`, `dist`,
  `*.egg-info`, and `.aotp`, and excludes `*.pyc`.
- Tests prove authorized crypto execution, combined campaign completion, pre-execution denial for
  missing TLS evidence, observation-only weak indicators, unsafe-action and unsafe-evidence
  denial, and non-git generated-cache exclusion.

All test execution was local, metadata-only, and network-silent. No live testing or external
target contact occurred.

## Validation

| Command | Result |
|---|---|
| `python3 -m compileall -q src tests` | Passed |
| `python3 -m pytest -q` | Unavailable: system Python has no `pytest` |
| `./.venv/bin/python -m pytest -q` | Passed, 229 tests |
| `./scripts/validate-repository-safety.sh` | Passed |
| `make check` | Unavailable at test phase: system Python has no `pytest` |
| `make PYTHON=.venv/bin/python check` | Passed, including 229 tests and safety validation |

Exact outputs are stored beside this summary.

## Known limitation

The host system Python does not include the repository's development dependencies. The
repository-supported virtual environment completed the full validation suite. No live validation
was attempted, by requirement.
