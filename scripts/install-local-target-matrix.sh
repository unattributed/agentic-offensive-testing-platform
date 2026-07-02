#!/usr/bin/env bash
set -euo pipefail

TARGET="crapi"
REPO=""
EVIDENCE_DIR=""
INSTALL_COMPOSE_IF_MISSING=0
LIVE=0

usage() {
  cat <<'USAGE'
Usage: scripts/install-local-target-matrix.sh --repo PATH --evidence-dir PATH [--target crapi] [--install-compose-if-missing] [--live]

Inventories the local system and records the selected vulnerable benchmark target
state. In Sprint 18H, Juice Shop is the proven live target. crAPI is registered as
the first additional planned target with benchmark metadata, but live crAPI setup
is intentionally fail-fast pending a deterministic runtime path on Parrot rootless
Podman Compose.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --install-compose-if-missing) INSTALL_COMPOSE_IF_MISSING=1; shift ;;
    --live) LIVE=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$REPO" ] || { echo "--repo is required" >&2; exit 2; }
[ -n "$EVIDENCE_DIR" ] || { echo "--evidence-dir is required" >&2; exit 2; }
[ "$TARGET" = "crapi" ] || { echo "only --target crapi is implemented in this follow-up" >&2; exit 2; }
mkdir -p "$EVIDENCE_DIR"

is_podman_emulated_docker() {
  command -v docker >/dev/null 2>&1 || return 1
  if docker --version 2>&1 | grep -qi 'podman'; then
    return 0
  fi
  if docker info 2>&1 | grep -Eqi 'podman|podman\.sock'; then
    return 0
  fi
  return 1
}

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
      >> "$EVIDENCE_DIR/crapi-live-pending-cleanup.log" 2>&1 || true
    podman pod rm -f pod_aotp-crapi >> "$EVIDENCE_DIR/crapi-live-pending-cleanup.log" 2>&1 || true
  fi
}

select_compose_inventory() {
  COMPOSE_STYLE="missing"
  COMPOSE_CMD=""
  if command -v podman >/dev/null 2>&1 && is_podman_emulated_docker && command -v podman-compose >/dev/null 2>&1; then
    COMPOSE_STYLE="podman-compose"
    COMPOSE_CMD="podman-compose"
  elif command -v podman-compose >/dev/null 2>&1; then
    COMPOSE_STYLE="podman-compose"
    COMPOSE_CMD="podman-compose"
  elif command -v docker >/dev/null 2>&1 && ! is_podman_emulated_docker && docker compose version >/dev/null 2>&1; then
    COMPOSE_STYLE="docker-compose-plugin"
    COMPOSE_CMD="docker compose"
  elif command -v docker-compose >/dev/null 2>&1 && ! is_podman_emulated_docker; then
    COMPOSE_STYLE="docker-compose-standalone"
    COMPOSE_CMD="docker-compose"
  fi
}

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "target=$TARGET"
  echo "repo=$REPO"
  echo "evidence_dir=$EVIDENCE_DIR"
  echo "live=$LIVE"
  echo "install_compose_if_missing=$INSTALL_COMPOSE_IF_MISSING"
  echo "current_user=$(id -un)"
  echo "home=$HOME"
  echo
  id
  echo
  uname -a
  echo
  [ -r /etc/os-release ] && cat /etc/os-release || true
  echo
  for tool in sudo curl unzip docker podman podman-compose docker-compose apt-get ss jq git; do
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

select_compose_inventory
{
  echo "compose_style=$COMPOSE_STYLE"
  echo "compose_cmd=$COMPOSE_CMD"
  echo "crapi_live_runtime_status=pending_unsupported"
  echo "crapi_live_runtime_reason=rootless Podman Compose did not produce deterministic healthy crAPI web on this Parrot host"
} > "$EVIDENCE_DIR/compose.txt"
cat "$EVIDENCE_DIR/compose.txt"

if [ "$LIVE" = "1" ]; then
  cleanup_partial_crapi_state
  cat > "$EVIDENCE_DIR/local-target-state.json" <<'EOF_STATE'
{
  "target_alias": "local-crapi",
  "network_exposure": "loopback-only",
  "registered_benchmark_profile": true,
  "implemented_live_target": false,
  "live_runtime_status": "pending_unsupported",
  "health_check": "not_run",
  "cleanup_attempted": true,
  "reason": "crAPI live runtime is pending until deterministic Parrot rootless Podman Compose startup is proven"
}
EOF_STATE
  echo "error: crAPI live runtime is pending_unsupported in Sprint 18H; no live crAPI containers were started" >&2
  exit 3
fi

cat > "$EVIDENCE_DIR/local-target-state.json" <<'EOF_STATE'
{
  "target_alias": "local-crapi",
  "network_exposure": "loopback-only",
  "registered_benchmark_profile": true,
  "implemented_live_target": false,
  "live_runtime_status": "pending_unsupported",
  "health_check": "not_run"
}
EOF_STATE

find "$EVIDENCE_DIR" -type f -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE_DIR/SHA256SUMS" 2>/dev/null || true

echo "local_target_matrix_install_status=0"
echo "target=$TARGET"
echo "compose_style=$COMPOSE_STYLE"
echo "crapi_live_runtime_status=pending_unsupported"
echo "evidence_dir=$EVIDENCE_DIR"
