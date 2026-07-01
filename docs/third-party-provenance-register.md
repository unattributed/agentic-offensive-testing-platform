# Third-party provenance register

This register contains source-level engineering decisions, not legal approvals.

| Component | Source | Version reference | Use | Inclusion | Status |
|---|---|---|---|---|---|
| WSTG mappings | OWASP Web Security Testing Guide | Versioned identifiers in case records | Method identifiers and public taxonomy | No source or prose copied | `accepted` |
| LangGraph adapter | LangGraph public Python API | Declared package range and installed inventory version | Durable orchestration interface | Dependency, no vendored source | `legal_review_required` |
| Python packaging metadata | Python Packaging User Guide | PEP 639 specification reviewed in Sprint 13 | Metadata field definitions | Reference only | `accepted` |
| OSMAP boundary | External OSMAP project | Private reviewed source reference required for operational use | Alias-only evidence contract | No dependency or copied code | `accepted` |
| Browser suite boundary | `ai-browser-security-test-suite` | Reviewed source commit required for operational use | Alias-only evidence contract | No dependency or copied code | `legal_review_required` |
| External templates and rules | Source-specific | Exact commit and bundle digest required | Optional private inputs | Never vendored by default | `legal_review_required` |

Any new external influence requires a row or a linked detailed provenance record before merge.
