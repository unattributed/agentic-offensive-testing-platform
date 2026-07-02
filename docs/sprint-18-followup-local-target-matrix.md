# Sprint 18 follow-up: local vulnerable target matrix

## Goal

Add a local target matrix registry and implement OWASP crAPI as the first additional live benchmark target after Juice Shop.

This follow-up expands AOTP beyond a single vulnerable web application while preserving the corrected Sprint 18 architecture:

- OWASP WSTG catalog remains canonical.
- The WSTG engine remains target-agnostic.
- Local targets are benchmark resources, not engine dependencies.
- Every live target must be reset before use.
- Every live target must remain loopback-only.

## Why crAPI first

Juice Shop is useful, but it is browser-heavy and does not fully stress modern API workflow behavior. crAPI adds API-centric testing pressure across authentication, authorization, object-level access, business logic, and multi-step workflows.

## Scope

This follow-up implements:

- local target registry
- crAPI profile
- crAPI benchmark manifest
- crAPI reset and install scripts
- local target matrix documentation
- validation tests

It does not yet add a crAPI campaign runner. That comes after the target can be installed, reset, verified, and represented safely.

## Acceptance

The follow-up is accepted when:

1. AOTP can enumerate implemented local benchmark targets.
2. Juice Shop and crAPI are both metadata-backed registry entries.
3. crAPI has a loopback-only profile and canonical WSTG benchmark mapping.
4. The crAPI reset script removes previous compose volumes and starts a clean local stack.
5. The script verifies crAPI and MailHog health.
6. The script rejects non-loopback listener exposure.
7. Focused tests and full project tests pass.
8. The implementation works without making crAPI a dependency of the WSTG engine.

## Evidence files

Expected live evidence includes:

- `inventory.txt`
- `compose.txt`
- `docker-compose.yml`
- `env.aotp`
- `compose-down.log`
- `compose-pull.log`
- `compose-up.log`
- `compose-ps.txt`
- `crapi-root.html`
- `mailhog-root.html`
- `listeners.txt`
- `local-target-state.json`
- `SHA256SUMS`

## Commit suggestion

```text
add local vulnerable target matrix
```


### Parrot Podman compose note

On the Parrot development host, `/usr/bin/docker` may be Podman emulation. Multi-container targets such as crAPI must use `podman-compose` when Docker is emulated by Podman. The local target matrix scripts therefore prefer `podman-compose`, install it when requested, and fully qualify crAPI compose image names before startup.


## Podman Compose v3 hotfix

Live Parrot evidence showed that podman-compose was selected correctly but crAPI still failed because upstream compose used unqualified backing images such as `postgres:14` and `mongo:4.4`. The reset script now fully qualifies every image, including `docker.io/library/postgres:14`, `docker.io/library/mongo:4.4`, and `docker.io/chromadb/chroma`, adds compose operation timeouts, and cleans partial crAPI containers on failure.


## crAPI live runtime status

crAPI is registered with profile metadata and WSTG benchmark mapping, but live runtime remains pending on the Parrot rootless Podman Compose host. Evidence showed partial compose startup without a healthy `crapi-web` listener on `127.0.0.1:8888`, so live crAPI is not accepted in Sprint 18H.


Status marker: crAPI live runtime pending.
