# Safe evaluator demonstration

This walkthrough uses only reserved placeholders and deterministic network-silent adapters. It
does not require or accept a target URL, credential, private scope, live flag, or external model.

## Fresh clone preparation

```sh
git clone <reviewed-repository-url> aotp-demo
cd aotp-demo
./scripts/bootstrap.sh
make check
```

Dependency installation may contact the configured package index. The demonstration itself sends
no network requests. An evaluator with a prepared environment can instead set
`AOTP_DEMO_PYTHON` to that environment's Python.

## Automated walkthrough

Run the demonstration in a new ignored workspace:

```sh
./scripts/run-evaluator-demo.sh /tmp/aotp-evaluator-demo
```

The directory must not already contain `.aotp` state. The script performs:

1. example scope validation;
2. module and case inventory;
3. policy-gated dry-run validation;
4. campaign planning;
5. the two-objective placeholder web campaign;
6. campaign event-chain verification; and
7. an evidence-only placeholder report.

Outputs are written under `/tmp/aotp-evaluator-demo/.aotp/demo/`. The final `summary.json` omits
timestamps, run identifiers, paths, and hashes so its safety-relevant fields are reproducible.

Expected properties:

- campaign status is `completed`;
- both approved placeholder objectives complete;
- request count is zero;
- evidence count is two;
- report-ready findings are zero; and
- the report declares that it does not infer vulnerabilities.

Do not add `--live`, replace aliases with targets, or use private materials during this
demonstration.
