#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="docker.io/bkimminich/juice-shop"
CONTAINER_NAME="aotp-juice-shop"
PORT="3000"
EVIDENCE_DIR=""
INSTALL_DOCKER_IF_MISSING="1"
ALLOW_NON_FOO="0"

usage() {
  cat <<'USAGE'
Usage: scripts/install-local-juice-shop-benchmark.sh [options]

Inventory the local Parrot/Debian system, ensure container tooling and curl are
present, pull OWASP Juice Shop, and start a clean loopback-only benchmark
container. Docker and Podman are both supported. Podman is preferred when it is
present because Parrot may expose /usr/bin/docker as Podman emulation.

Options:
  --evidence-dir DIR             Write install evidence into DIR
  --image IMAGE                  Container image, default docker.io/bkimminich/juice-shop
  --container-name NAME          Container name, default aotp-juice-shop
  --port PORT                    Host port, default 3000
  --no-install-docker            Fail if Docker/Podman tooling is missing instead of installing docker.io
  --allow-non-foo                Allow execution by a user other than foo
  -h, --help                     Show this help
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --image) IMAGE="$2"; shift 2 ;;
    --container-name) CONTAINER_NAME="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --no-install-docker) INSTALL_DOCKER_IF_MISSING="0"; shift ;;
    --allow-non-foo) ALLOW_NON_FOO="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$EVIDENCE_DIR" ]; then
  EVIDENCE_DIR="$HOME/Downloads/aotp-juice-shop-install-$(date -u +%Y%m%d-%H%M%SZ)"
fi
mkdir -p "$EVIDENCE_DIR"
LOG="$EVIDENCE_DIR/install-local-juice-shop-benchmark.log"
exec > >(tee -a "$LOG") 2>&1

fail() {
  echo "error=$*" >&2
  exit 1
}

current_user="$(id -un)"
if [ "$ALLOW_NON_FOO" != "1" ] && [ "$current_user" != "foo" ]; then
  fail "this benchmark must be installed and managed by user foo, current_user=$current_user"
fi

case "$PORT" in
  ''|*[!0-9]*) fail "port must be numeric" ;;
esac
if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
  fail "port must be between 1024 and 65535"
fi

command -v sudo >/dev/null 2>&1 || fail "sudo is required"
sudo -n true || fail "passwordless sudo is required for user $current_user"
command -v curl >/dev/null 2>&1 || fail "curl is required"

container_tool=""
container_style=""
container_cmd=()
select_container_tool() {
  container_tool=""
  container_style=""
  container_cmd=()

  if command -v podman >/dev/null 2>&1; then
    container_tool="$(command -v podman)"
    container_style="podman"
    container_cmd=("$container_tool")
    return 0
  fi

  if command -v docker >/dev/null 2>&1; then
    container_tool="$(command -v docker)"
    if docker --version 2>&1 | grep -qi podman; then
      container_style="podman-docker-emulation"
      container_cmd=("$container_tool")
    elif docker info >/dev/null 2>&1; then
      container_style="docker-rootless-or-user-group"
      container_cmd=("$container_tool")
    else
      container_style="docker-sudo"
      container_cmd=(sudo -n "$container_tool")
    fi
    return 0
  fi

  return 1
}

if ! select_container_tool; then
  [ "$INSTALL_DOCKER_IF_MISSING" = "1" ] || fail "container tooling is missing and --no-install-docker was requested"
  command -v apt-get >/dev/null 2>&1 || fail "container tooling is missing and apt-get is unavailable"
  echo "container_tool_missing=true"
  sudo -n apt-get update
  sudo -n apt-get install -y docker.io
  select_container_tool || fail "container tooling is still unavailable after docker.io install"
fi

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "current_user=$current_user"
  echo "home=$HOME"
  echo "pwd=$PWD"
  echo "image=$IMAGE"
  echo "container_name=$CONTAINER_NAME"
  echo "port=$PORT"
  echo "install_docker_if_missing=$INSTALL_DOCKER_IF_MISSING"
  echo "container_tool=$container_tool"
  echo "container_style=$container_style"
  printf 'container_cmd='
  printf '%q ' "${container_cmd[@]}"
  echo
  echo
  id
  echo
  groups
  echo
  uname -a
  echo
  if [ -r /etc/os-release ]; then cat /etc/os-release; fi
  echo
  for cmd in sudo curl podman docker systemctl service apt-get python3 git jq ss ip; do
    if command -v "$cmd" >/dev/null 2>&1; then
      echo "$cmd=$(command -v "$cmd")"
      "$cmd" --version 2>&1 | head -8 || true
    else
      echo "$cmd=missing"
    fi
    echo
  done
} > "$EVIDENCE_DIR/preflight-inventory.txt" 2>&1
cat "$EVIDENCE_DIR/preflight-inventory.txt"

if [ "$container_style" = "docker-sudo" ] || [ "$container_style" = "docker-rootless-or-user-group" ]; then
  if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files docker.service >/dev/null 2>&1; then
    sudo -n systemctl enable --now docker || true
  elif command -v service >/dev/null 2>&1 && service docker status >/dev/null 2>&1; then
    sudo -n service docker start || true
  else
    echo "docker_service=not_present_or_not_required"
  fi
else
  echo "docker_service=not_required_for_$container_style"
fi

"${container_cmd[@]}" version > "$EVIDENCE_DIR/container-version.txt" 2>&1 || fail "container engine is not available"
"${container_cmd[@]}" pull "$IMAGE" | tee "$EVIDENCE_DIR/container-pull.log"
"${container_cmd[@]}" image inspect "$IMAGE" > "$EVIDENCE_DIR/container-image-inspect.json"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$script_dir/juice-shop-local-reset.sh" \
  --evidence-dir "$EVIDENCE_DIR/reset" \
  --image "$IMAGE" \
  --container-name "$CONTAINER_NAME" \
  --port "$PORT"

find "$EVIDENCE_DIR" -type f -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE_DIR/SHA256SUMS" 2>/dev/null || true

echo "juice_shop_install_status=0"
echo "container_style=$container_style"
echo "base_url=http://127.0.0.1:$PORT/"
echo "evidence_dir=$EVIDENCE_DIR"
