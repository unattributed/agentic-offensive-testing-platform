# Sprint 18 follow-up: local Juice Shop WSTG campaign benchmark

## Purpose

Sprint 18 corrected AOTP around a canonical OWASP WSTG v4.2 catalog and a generic
WSTG planning engine. This follow-up adds a local-only OWASP Juice Shop benchmark
resource so future development can validate that the engine can run real testing
campaigns against a known intentionally vulnerable application.

This is not a new sprint. It is a Sprint 18 follow-up because it strengthens the
corrected WSTG engine foundation with a repeatable local target.

## Non-negotiable constraints

- The benchmark runs on the Parrot development system as user `foo`.
- Passwordless sudo is required for Docker management.
- The service binds only to `127.0.0.1:3000`.
- The container is removed and recreated before every campaign.
- No persistent mounts or host volumes are allowed.
- The benchmark does not replace future authorized bug bounty testing.
- The benchmark does not define WSTG coverage. The canonical WSTG catalog does.

## Acceptance

The follow-up is accepted when AOTP can:

1. Inventory the local system before installing or starting the benchmark.
2. Install Docker from the local Debian or Parrot package manager when Docker is
   missing and passwordless sudo is available.
3. Pull the `docker.io/bkimminich/juice-shop` image.
4. Start Juice Shop on loopback only.
5. Prove the target is healthy before a campaign uses it.
6. Prove previous challenge state is cleared by removing and recreating the
   container before each campaign.
7. Map broad Juice Shop vulnerability classes to canonical WSTG v4.2 entries
   without embedding challenge solutions.
8. Update development planning so future executable WSTG work uses this local
   benchmark before moving to authorized bug bounty targets.

## Development evidence

- `src/aotp/lab_targets/juice_shop.py`
- `src/aotp/benchmarks/juice_shop.py`
- `scripts/install-local-juice-shop-benchmark.sh`
- `scripts/juice-shop-local-reset.sh`
- `scripts/run-sprint18-followup-local-juice-shop-validation.sh`
- `docs/lab-targets/juice-shop-local.md`
- `tests/test_juice_shop_local_profile.py`
- `tests/test_juice_shop_benchmark_mapping.py`
- `tests/test_juice_shop_local_scripts.py`

## Closeout command

```sh
scripts/run-sprint18-followup-local-juice-shop-validation.sh \
  --repo "$HOME/Workspace/agentic-offensive-testing-platform" \
  --evidence-dir "$HOME/Downloads/aotp-sprint18-followup-local-juice-shop-$(date -u +%Y%m%d-%H%M%SZ)" \
  --install-local-juice-shop
```

Git commit comment:

```text
add local juice shop sprint 18 benchmark
```


## Parrot container runtime note

Parrot may provide `/usr/bin/docker` as Podman emulation. The local benchmark scripts therefore detect Podman explicitly, use the fully qualified `docker.io/bkimminich/juice-shop` image name, and avoid requiring a `docker.service` when Podman is the active runtime.
