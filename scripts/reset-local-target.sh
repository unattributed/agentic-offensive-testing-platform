#!/usr/bin/env bash
set -euo pipefail

TARGET=""
REPO=""
EVIDENCE_DIR=""
INSTALL_COMPOSE_IF_MISSING=0

usage() {
  cat <<'USAGE'
Usage: scripts/reset-local-target.sh --repo PATH --target crapi --evidence-dir PATH [--install-compose-if-missing]

Records crAPI as a registered planned benchmark target and fails fast for live
reset. Sprint 18H evidence showed rootless Podman Compose could leave partial
crAPI state on this Parrot host. Until a deterministic runtime path is proven,
this script does not start crAPI. It cleans partial crAPI containers and writes
a pending-runtime evidence record.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --install-compose-if-missing) INSTALL_COMPOSE_IF_MISSING=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$REPO" ] || { echo "--repo is required" >&2; exit 2; }
[ "$TARGET" = "crapi" ] || { echo "only --target crapi is implemented" >&2; exit 2; }
[ -n "$EVIDENCE_DIR" ] || { echo "--evidence-dir is required" >&2; exit 2; }
mkdir -p "$EVIDENCE_DIR"

cleanup_partial_crapi_state() {
  if command -v podman >/dev/null 2>&1; then
    podman rm -f \
      crapi-chatbot \
      chromadb \
      crapi-web \
      api.mypremiumdealership.com \
      postgresdb \
      crapi-identity \
      mongodb \
      crapi-community \
      mailhog \
      crapi-workshop \
      > "$EVIDENCE_DIR/direct-container-cleanup.log" 2>&1 || true
    podman pod rm -f pod_aotp-crapi >> "$EVIDENCE_DIR/direct-container-cleanup.log" 2>&1 || true
    podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}' > "$EVIDENCE_DIR/post-cleanup-podman-ps.txt" 2>&1 || true
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp > "$EVIDENCE_DIR/post-cleanup-listeners.txt" 2>&1 || true
  fi
}

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "target=$TARGET"
  echo "repo=$REPO"
  echo "evidence_dir=$EVIDENCE_DIR"
  echo "current_user=$(id -un)"
  echo "install_compose_if_missing=$INSTALL_COMPOSE_IF_MISSING"
  echo "crapi_live_runtime_status=pending_unsupported"
  echo "crapi_live_runtime_reason=deterministic Parrot rootless Podman Compose startup is not yet proven"
  echo
  id
  echo
  uname -a
  echo
  for tool in podman podman-compose docker docker-compose ss curl; do
    if command -v "$tool" >/dev/null 2>&1; then
      echo "$tool=$(command -v "$tool")"
      "$tool" --version 2>&1 | head -n 3 || true
    else
      echo "$tool=missing"
    fi
    echo
  done
} > "$EVIDENCE_DIR/inventory.txt" 2>&1
cat "$EVIDENCE_DIR/inventory.txt"

cleanup_partial_crapi_state

cat > "$EVIDENCE_DIR/local-target-state.json" <<'EOF_STATE'
{
  "target_alias": "local-crapi",
  "base_url": "http://127.0.0.1:8888/",
  "mailhog_url": "http://127.0.0.1:8025/",
  "network_exposure": "loopback-only",
  "registered_benchmark_profile": true,
  "implemented_live_target": false,
  "live_runtime_status": "pending_unsupported",
  "health_check": "not_run",
  "cleanup_attempted": true
}
EOF_STATE

find "$EVIDENCE_DIR" -type f -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE_DIR/SHA256SUMS" 2>/dev/null || true

echo "error: crAPI live reset is pending_unsupported in Sprint 18H; partial crAPI state was cleaned" >&2
exit 3
