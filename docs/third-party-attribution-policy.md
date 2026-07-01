# Third-party attribution and provenance policy

This policy is an engineering control, not legal advice.

## Required record

Before code, documentation, data, templates, generated assets, or dependencies influenced by an
external source can merge, the reviewer must record:

1. internal change or component identifier;
2. source type and whether content was copied, adapted, generated, or referenced only;
3. upstream name, author or owner, canonical URL, and immutable version or commit;
4. upstream copyright and exact license expression;
5. files, interfaces, behaviors, or ideas consulted;
6. clean-room separation method when applicable;
7. required notices, source obligations, attribution, and redistribution constraints;
8. compatibility decision for the proprietary distribution;
9. reviewer alias, decision date, and decision status; and
10. legal-review reference when the status is not clearly accepted.

Links without an immutable version are insufficient. Package metadata alone is evidence for
triage, not final approval.

## Merge gate

| Status | Merge result |
|---|---|
| `accepted` | May merge after normal technical review |
| `legal_review_required` | Blocked |
| `rejected` | Blocked |
| missing or incomplete | Blocked |

Reviewers must reject copied material with unknown origin, incompatible terms, missing notices, or
an unverifiable author. Removing an attribution notice never resolves an underlying license
obligation.

## Clean-room boundary

Reference work is limited to documented behavior, public interfaces, formats, and interoperability
requirements. The implementer must not copy source, tests, comments, documentation prose,
templates, or distinctive internal structure. The record identifies the consulted materials and
the independently produced design. A reviewer compares provenance and implementation before merge.

External tools should remain separate processes or evidence sources unless a reviewed dependency
decision explicitly permits inclusion. Their outputs and rule sets retain their own licenses.

## Generated material

Generated code, text, images, and test data require the generating tool, model or generator
version, prompt or input provenance when retainable, human reviewer, and source-material review.
Generated output with uncertain training-source or input rights remains blocked.
