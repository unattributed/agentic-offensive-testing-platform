# Local OWASP Juice Shop benchmark target

AOTP uses OWASP Juice Shop as a local-only benchmark target for validating WSTG
campaign behavior against a known intentionally vulnerable application.

## Safety boundary

The benchmark is constrained to the Parrot development system and must bind only
to loopback:

```text
http://127.0.0.1:3000/
```

The container must not be exposed to the LAN, WAN, public internet, or shared
production hosts. It must not use persistent host mounts or Docker volumes.

## Required reset behavior

Before every AOTP campaign, the local benchmark must be reset by removing the old
container and starting a new container from the Juice Shop image:

```text
docker rm -f aotp-juice-shop
docker run -d --name aotp-juice-shop -p 127.0.0.1:3000:3000 bkimminich/juice-shop
```

The project script `scripts/juice-shop-local-reset.sh` performs the reset and
records evidence proving:

- the current user is `foo`, unless explicitly overridden for CI-style checks,
- passwordless sudo is available,
- Docker is available,
- the container is freshly recreated,
- the port binding is exactly `127.0.0.1:3000:3000`,
- no persistent mounts are attached,
- the application responds on `http://127.0.0.1:3000/`.

## Project role

Juice Shop is a benchmark resource, not the WSTG engine. The canonical standard
remains the OWASP WSTG catalog in `src/aotp/wstg/catalog.py`. The local Juice
Shop profile only provides a controlled target for campaign validation.

The benchmark must be used after campaign execution to compare observed WSTG
coverage against expected vulnerability classes. It must not be used as a source
of hardcoded solutions or challenge-specific exploit shortcuts.


## Parrot container runtime note

Parrot may provide `/usr/bin/docker` as Podman emulation. The local benchmark scripts therefore detect Podman explicitly, use the fully qualified `docker.io/bkimminich/juice-shop` image name, and avoid requiring a `docker.service` when Podman is the active runtime.
