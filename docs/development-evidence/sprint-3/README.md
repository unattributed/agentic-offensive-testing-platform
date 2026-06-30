# Sprint 3 closeout evidence

Sprint 3 delivers a usable, integrity-checked pipeline from captured evidence through verifier decision, finding lifecycle and human-review reporting.

## Slice commits

| Slice | Commit | Functional result |
|---|---|---|
| 3.1 evidence manifest | `d8bb407` | Strict atomic manifest with canonical integrity hash |
| 3.2 redaction | `6ad12d6` | Recursive field-aware secret detection and value-free reports |
| 3.3 artifact hashing | `8f6cbbd` | Symlink-safe artifact registry and mutation detection |
| 3.4 verifier verdict | `83e1678` | Evidence-bound five-verdict record and CLI |
| 3.5 finding lifecycle | `55c6ea2` | Verified-fail-only candidate creation, fingerprint and review history |
| 3.6 reporting | `6c129bb` | Verified evidence and report-ready candidate rendering |

## Full validation

```text
python3 -m compileall -q src tests
python3 -m pytest
114 passed in 0.62s
./scripts/validate-repository-safety.sh
repository safety validation passed
python3 -m pip check
No broken requirements found.
```

## Functional pipeline smoke

An isolated CLI workflow:

1. executed a deterministic dry-run case and wrote evidence;
2. recorded a separate fail verdict bound to the manifest hash;
3. created a fingerprinted candidate;
4. moved it through human review, confirmation and report readiness; and
5. generated a human-review draft containing exactly one evidence-backed finding and one verified evidence appendix entry.

No target traffic, real program data or private evidence was used.

## Sprint acceptance

- Modified manifests, artifacts, verifier records and candidates are rejected.
- Secret findings never expose matched values.
- Pass and fail verdicts require evidence references.
- Only fail verification can create a finding candidate.
- Severity, confidence and evidence strength remain separate.
- Confirmation requires human validation.
- Reports refuse modified evidence and exclude candidates not ready for report.
- Report language is recorded input only and does not invent impact or remediation.
