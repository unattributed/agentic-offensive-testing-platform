# Local vulnerable target matrix

This document defines the local vulnerable target matrix used to validate AOTP WSTG campaign behavior after the Sprint 18 WSTG catalog, Juice Shop benchmark, and Juice Shop agentic campaign follow-ups.

The matrix exists to test the engine. It must not become the engine.

## Safety baseline

All implemented targets must satisfy these constraints before AOTP can use them:

- loopback-only listener exposure
- reset before every campaign
- fresh target state for every run
- no target-specific exploit shortcuts in the WSTG engine
- benchmark mappings based on canonical WSTG IDs
- evidence captured outside the container runtime
- project validation through the repository `.venv`

## Implemented targets

| Alias | Target | Purpose | URL | Status |
|---|---|---|---|---|
| `local-juice-shop` | OWASP Juice Shop | Modern browser-heavy vulnerable web application benchmark | `http://127.0.0.1:3000/` | Implemented |
| `local-crapi` | OWASP crAPI | Modern API, authorization, authentication, and business-logic benchmark | `http://127.0.0.1:8888/` | Implemented in this follow-up |

## crAPI role

crAPI is the first additional planned target after Juice Shop. It adds API-heavy and workflow-heavy coverage that Juice Shop alone does not adequately stress:

- API route and architecture discovery
- object-level authorization review
- authentication and reset workflows
- multi-step business-logic planning
- SSRF-adjacent and server-side request behavior
- MailHog-backed local email observation

## Local-only deployment policy

The crAPI reset script downloads the official OWASP crAPI main archive, enters `crAPI-main/deploy/docker`, starts the official compose file with `LISTEN_IP=127.0.0.1`, and verifies exposed listeners. It removes previous compose state with volumes before start so old application state does not carry into a campaign.

Expected exposed ports:

| Port | Purpose |
|---:|---|
| `127.0.0.1:8888` | crAPI web application |
| `127.0.0.1:8025` | MailHog web UI |
| `127.0.0.1:30080` | alternate HTTP mapping from official compose |
| `127.0.0.1:8443` | HTTPS mapping from official compose |
| `127.0.0.1:30443` | alternate HTTPS mapping from official compose |
| `127.0.0.1:5500` | crAPI chatbot MCP service from official compose |

A non-loopback listener for any target port is a failure.

## Commands

Inventory and validate without live crAPI setup:

```sh
scripts/run-sprint18-followup-local-target-matrix-validation.sh \
  --repo "$PWD" \
  --evidence-dir "$HOME/Downloads/aotp-target-matrix-validation"
```

Install compose support when needed and reset crAPI:

```sh
scripts/run-sprint18-followup-local-target-matrix-validation.sh \
  --repo "$PWD" \
  --evidence-dir "$HOME/Downloads/aotp-target-matrix-validation" \
  --install-compose-if-missing \
  --live-crapi
```

Reset crAPI directly:

```sh
scripts/reset-local-target.sh \
  --repo "$PWD" \
  --target crapi \
  --evidence-dir "$HOME/Downloads/aotp-crapi-reset" \
  --install-compose-if-missing
```

## Future target order

The next local target additions should be DVWA verifier mode, WebGoat and WebWolf workflow mode, then a verified Python microframework target. Each must be added through the registry with reset and health contracts before any campaign runner depends on it.


### Parrot Podman compose note

On the Parrot development host, `/usr/bin/docker` may be Podman emulation. Multi-container targets such as crAPI must use `podman-compose` when Docker is emulated by Podman. The local target matrix scripts therefore prefer `podman-compose`, install it when requested, and fully qualify crAPI compose image names before startup.


## Podman Compose v3 hotfix

Live Parrot evidence showed that podman-compose was selected correctly but crAPI still failed because upstream compose used unqualified backing images such as `postgres:14` and `mongo:4.4`. The reset script now fully qualifies every image, including `docker.io/library/postgres:14`, `docker.io/library/mongo:4.4`, and `docker.io/chromadb/chroma`, adds compose operation timeouts, and cleans partial crAPI containers on failure.


## crAPI live runtime status

crAPI is registered with profile metadata and WSTG benchmark mapping, but live runtime remains pending on the Parrot rootless Podman Compose host. Evidence showed partial compose startup without a healthy `crapi-web` listener on `127.0.0.1:8888`, so live crAPI is not accepted in Sprint 18H.


Status marker: crAPI live runtime pending.
