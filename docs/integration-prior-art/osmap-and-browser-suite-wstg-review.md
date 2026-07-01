# OSMAP and browser-suite WSTG prior-art review

## What was reviewed

This Sprint 4 design note is prepared for a clean-room review of local, separately cloned prior-art repositories:

- `unattributed/OSMAP`, especially `maint/wstg-testing-pack/`, WSTG scenario matrix files, WSTG ASVS mapping files, WSTG runner behavior, coverage documentation, due-diligence documentation, remediation documentation, V13 WSTG assurance material, integrity material, credentialed release material, adversarial validation material, WSTG gates, and release summaries.
- `unattributed/ai-browser-security-test-suite`, especially evidence schema contracts, local proxy evidence workflow, proxy runners, browser runners, hidden DOM labs, DOM/source/rendered-page mismatch labs, screenshot and visual deception labs, iframe and frame-tree labs, storage-state boundary work, synthetic sensitive-data handling, capstone evidence package generation, practical lab validation, and student-readiness checks.

The runner inventories local file names when those repositories are present, but it does not copy, import, vendor, or commit their implementation files.

## Concepts adopted

AOTP adopts these concepts only as native contracts:

- version-aware WSTG case mappings,
- deterministic WSTG case identifiers,
- explicit approved and denied action lists,
- objective-specific human approval requirements,
- evidence-producing dry-run workflow,
- assurance and closeout discipline,
- SHA256 evidence expectations,
- DOM, rendered-page, screenshot, frame-tree, browser-context, storage-state, and proxy-capture artifact categories,
- external local evidence references by alias, relative path, SHA256, provenance, source project or adapter contract, and redaction status.

## What was intentionally not copied

AOTP does not copy or vendor OSMAP code, browser-suite code, runner implementations, generated evidence, screenshots, traces, captures, private target data, scenario files, or release evidence. It does not import either project as a dependency.

## Clean-room and license boundary

OSMAP and `ai-browser-security-test-suite` remain separate projects. Sprint 4 uses clean-room concepts and AOTP-native data contracts only. External evidence is referenced by metadata, never embedded. Separate license obligations remain with the source projects and must be reviewed before any broader licensing or distribution change.

## How OSMAP informs WSTG case and mapping design

OSMAP informs AOTP's WSTG design through taxonomy discipline, version-aware mapping fields, scenario matrix thinking, evidence-first WSTG execution flow, explicit closeout records, and release-gate expectations. The v0.1 implementation converts those ideas into dry-run case registry records and policy-gated case execution models. Sprint 14 onward extends that foundation into campaign-governed native tool execution without importing OSMAP code. Sprint 17 adds reusable WSTG coverage planning, and the Sprint 17 follow-up adds an OSMAP-inspired execution adapter contract without copying, vendoring, or invoking OSMAP.

## How the browser suite informs browser evidence modeling

The browser suite informs evidence categories for DOM snapshots, rendered-page summaries, screenshot placeholders, frame-tree placeholders, browser-context placeholders, storage-state placeholders, and proxy-capture placeholders. AOTP models these as inert artifact placeholders and external local evidence references only. No live Playwright, proxy, or browser execution is added in Sprint 4.

## External local evidence reference model

AOTP external local evidence references require:

- alias,
- relative path,
- SHA256,
- provenance,
- source project or adapter contract,
- redaction status.

Path policy rejects path escape, symlink abuse, redaction bypass, malformed SHA256, and absolute paths unless a future policy explicitly supports a safe absolute-path mode.

## Deferred live adapter readiness

Future live readiness remains deferred for Playwright navigation, ZAP passive or spider work, mitmproxy capture, OSMAP external process execution, and browser-suite external process execution unless a later sprint implements and validates a specific governed wrapper. The Sprint 17 follow-up execution adapter is a contract-only bridge: it can record governed execution intent, OSMAP-style result semantics, redacted evidence references, coverage updates, and evidence-bound finding candidates, but it does not enable network-capable behavior. Future work must add explicit approvals, private scope requirements, dependency checks, redaction checks, and live adapter validation before any network-capable behavior is enabled.
