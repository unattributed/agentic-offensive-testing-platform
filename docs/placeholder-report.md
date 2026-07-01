# Placeholder evidence report

`examples/demo/placeholder-report.example.md` is generated from one fixed, integrity-verified
placeholder manifest by `scripts/generate-placeholder-report.py`.

The sample contains no finding candidate because none completed evidence verification and human
review. It reports:

- one verified placeholder evidence record;
- zero report-ready findings;
- zero network requests in the source manifest;
- an `inconclusive` verifier verdict;
- a reserved local target alias; and
- an explicit statement that vulnerabilities, impact, exploitability, affected assets, and
  remediation are not inferred.

Reproduce it without contacting a service:

```sh
PYTHONPATH=src ./.venv/bin/python scripts/generate-placeholder-report.py \
  --output /tmp/placeholder-report.md
cmp /tmp/placeholder-report.md examples/demo/placeholder-report.example.md
```

Generated reports for private operations belong under ignored local paths, never in the
repository.
