# Operator metrics

AOTP tracks a bounded measurement period, manual and agent-assisted hours, requests, cases,
candidates, confirmed, submitted, accepted, rejected, and duplicate counts, bounty amount, and
estimated tool cost. Monetary amounts remain separate and carry one currency code.

Metrics are private aggregate values. Their schema has no target, asset, program, evidence, finding,
or personal-data fields. Counts are non-negative and internally consistent. Outcomes measure
workflow efficiency, not guaranteed future income. Metrics files are local and mode `0600`.
