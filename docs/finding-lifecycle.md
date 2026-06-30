# Finding lifecycle

States are `observed`, `candidate`, `needs_reproduction`, `needs_human_review`, `confirmed`, `duplicate_risk`, `out_of_scope`, `not_security_impacting`, `ready_for_report`, `submitted_manually`, `accepted`, `rejected`, and `paid`.

Evidence is required from the first observation. Confirmation and report readiness require human validation. Severity candidate, confidence, evidence strength, and human validation are separate fields. Submission is manual.

Candidate creation requires an integrity-verified manifest and a matching `fail` verification record. Lifecycle transitions append reviewer and timestamp history. Reports include only `ready_for_report` candidates whose evidence hash is present in the selected report evidence set.
