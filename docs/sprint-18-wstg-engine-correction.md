# Sprint 18 WSTG Engine Correction

Sprint 18 is corrected to focus on reusable AOTP-owned WSTG engine capability.

OSMAP remains a narrow application-specific reference example only. Code patterns from OSMAP may be reused when they are generalized, renamed, and covered by AOTP-owned tests. OSMAP source paths, imports, routes, and assumptions must not be required by the core WSTG engine.

## Delivered capability

- Canonical OWASP WSTG v4.2 catalog in `src/aotp/wstg/catalog.py`.
- Complete 97-test WSTG v4.2 matrix across INFO, CONF, IDNT, ATHN, ATHZ, SESS, INPV, ERRH, CRYP, BUSL, CLNT, and APIT.
- Generic WSTG planning engine in `src/aotp/wstg/engine.py`.
- Planning dispositions for ready, deferred, and denied test cases.
- Safety gates for passive, safe active, intrusive active, authentication, multi-role, privileged, source-assisted, and adapter-family approval.
- Strategy-map correction so official WSTG identifiers cannot be assigned to internal AOTP abstractions with incorrect titles.
- Regression test that prevents the core WSTG package from depending on OSMAP.

## Acceptance statement

Sprint 18 is accepted when AOTP can load a complete canonical OWASP WSTG v4.2 catalog, build a governed plan for every WSTG test case against an authorized target, explain which tests are ready or deferred, and avoid any OSMAP dependency in the core WSTG engine.

## Non-goals

- Full exploitation automation for every WSTG test.
- Copying PortSwigger lab content.
- Treating OSMAP as the WSTG engine.
- Running active tests without explicit authorization and scope approval.
