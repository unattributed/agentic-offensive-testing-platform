# Slice 3.6 evidence: evidence-only reporting

Reports now verify every manifest and artifact before rendering. Only candidates in `ready_for_report` with matching evidence hashes are included as findings. Other candidates are counted as excluded without promoting their claims.

Output is explicitly a human-review draft and includes recorded aliases, case IDs, severity candidate, confidence, evidence strength, fingerprints and manifest hashes. It does not generate impact, exploitability or remediation.

```text
python3 -m pytest tests/test_reporter.py tests/test_finding_candidate.py tests/test_finding_lifecycle.py tests/test_cli.py
15 passed in 0.25s
```

Tests prove report-ready inclusion, exclusion of unreviewed observations, and refusal to report modified evidence.
