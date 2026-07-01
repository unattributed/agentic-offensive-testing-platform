# Bug Bounty Mode

AOTP supports authorized HackerOne and Bugcrowd workflows without enrolling in programs,
submitting findings, or disclosing material automatically.

The operator may ingest program policy from saved HTML, pasted text, Markdown, or PDF into a
private program profile. AOTP normalizes allowed and excluded assets, domains, paths, APIs, mobile
targets, testing categories, rates, and disclosure terms. Ambiguous or conflicting policy blocks
live execution until the operator records a decision.

Bug bounty campaigns default to low-noise passive and browser-first tools. Active scanning or
higher-risk validation requires explicit permission. The agent cannot add a target outside the
normalized scope.

Duplicate and prior-art review occurs before report readiness. The report acceptance gate requires
an affected asset, reproducible steps, impact supported by evidence, limitations, evidence
references, and a scope statement. Export creates a manual-only submission package. AOTP has no
automatic submission or disclosure path.
