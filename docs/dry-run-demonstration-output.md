# Dry-run demonstration output

The evaluator demonstration writes generated output under `.aotp/demo/` in its selected workspace.
That directory is ignored and must not be committed.

The tracked sample at `examples/demo/dry-run-summary.example.json` is a normalized placeholder
summary. A successful run must match it exactly. This proves:

- only the fixed placeholder campaign ran;
- both approved objectives completed;
- no network request was sent;
- two integrity-managed evidence records were created locally;
- no finding was report-ready; and
- the generated report declared its limitations.

Timestamps, run IDs, paths, event hashes, and manifest hashes are intentionally excluded from the
sample because they vary safely between executions. The underlying generated artifacts retain
those fields for local verification.
