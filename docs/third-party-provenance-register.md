# Third-party provenance register

This register contains source-level engineering decisions, not legal approvals.

| Component | Source | Version reference | Use | Inclusion | Status |
|---|---|---|---|---|---|
| WSTG mappings | OWASP Web Security Testing Guide | Versioned identifiers in case records | Method identifiers and public taxonomy | No source or prose copied | `accepted` |
| LangGraph adapter | LangGraph public Python API | Declared package range and installed inventory version | Durable orchestration interface | Dependency, no vendored source | `legal_review_required` |
| Python packaging metadata | `https://peps.python.org/pep-0639/` | PEP 639 final specification | Metadata field definitions | Reference only | `accepted` |
| Repository checkout action | `https://github.com/actions/checkout` | Commit `de0fac2e4500dabe0009e67214ff5f5447ce83dd` | CI checkout | Remote action, no vendored source | `accepted` |
| Python setup action | `https://github.com/actions/setup-python` | Commit `a309ff8b426b58ec0e2a45f0f869d46889d02405` | CI runtime setup | Remote action, no vendored source | `accepted` |
| OSMAP boundary | External OSMAP project | Private reviewed source reference required for operational use | Alias-only evidence contract | No dependency or copied code | `accepted` |
| Browser suite boundary | `ai-browser-security-test-suite` | Reviewed source commit required for operational use | Alias-only evidence contract | No dependency or copied code | `legal_review_required` |
| External templates and rules | Source-specific | Exact commit and bundle digest required | Optional private inputs | Never vendored by default | `legal_review_required` |

Any new external influence requires a row or a linked detailed provenance record before merge.
