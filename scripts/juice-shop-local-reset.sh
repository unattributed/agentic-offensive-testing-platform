#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="docker.io/bkimminich/juice-shop"
CONTAINER_NAME="aotp-juice-shop"
HOST="127.0.0.1"
PORT="3000"
EVIDENCE_DIR=""
PULL_IMAGE="0"
ALLOW_NON_FOO="0"

usage() {
  cat <<'USAGE'
Usage: scripts/juice-shop-local-reset.sh [options]

Reset and start a clean loopback-only OWASP Juice Shop container for AOTP.
Docker and Podman are both supported. Podman is preferred when present.

Options:
  --evidence-dir DIR      Write reset evidence into DIR
  --image IMAGE           Container image, default docker.io/bkimminich/juice-shop
  --container-name NAME   Container name, default aotp-juice-shop
  --port PORT             Host port, default 3000
  --pull                  Pull the image before reset
  --allow-non-foo         Allow execution by a user other than foo
  -h, --help              Show this help
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --image) IMAGE="$2"; shift 2 ;;
    --container-name) CONTAINER_NAME="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --pull) PULL_IMAGE="1"; shift ;;
    --allow-non-foo) ALLOW_NON_FOO="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$EVIDENCE_DIR" ]; then
  EVIDENCE_DIR="$HOME/Downloads/aotp-juice-shop-reset-$(date -u +%Y%m%d-%H%M%SZ)"
fi
mkdir -p "$EVIDENCE_DIR"
LOG="$EVIDENCE_DIR/juice-shop-reset.log"
exec > >(tee -a "$LOG") 2>&1

fail() {
  echo "error=$*" >&2
  exit 1
}

current_user="$(id -un)"
if [ "$ALLOW_NON_FOO" != "1" ] && [ "$current_user" != "foo" ]; then
  fail "this benchmark must be managed by user foo, current_user=$current_user"
fi

[ "$HOST" = "127.0.0.1" ] || fail "host binding must remain 127.0.0.1"
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
select_container_tool || fail "container tooling is required, run scripts/install-local-juice-shop-benchmark.sh first"

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "current_user=$current_user"
  echo "image=$IMAGE"
  echo "container_name=$CONTAINER_NAME"
  echo "host_binding=$HOST:$PORT:3000"
  echo "evidence_dir=$EVIDENCE_DIR"
  echo "container_tool=$container_tool"
  echo "container_style=$container_style"
  printf 'container_cmd='
  printf '%q ' "${container_cmd[@]}"
  echo
  echo
  id
  echo
  uname -a
  echo
  "$container_tool" --version || true
  "${container_cmd[@]}" version || true
} > "$EVIDENCE_DIR/inventory.txt" 2>&1
cat "$EVIDENCE_DIR/inventory.txt"

if [ "$PULL_IMAGE" = "1" ]; then
  "${container_cmd[@]}" pull "$IMAGE"
fi

"${container_cmd[@]}" rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

container_id="$("${container_cmd[@]}" run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  --label aotp.purpose=aotp-wstg-campaign-benchmark \
  --label aotp.target=local-juice-shop \
  --label aotp.network_exposure=loopback-only \
  --label aotp.reset_required=true \
  -p "$HOST:$PORT:3000" \
  "$IMAGE")"

echo "container_id=$container_id"

base_url="http://$HOST:$PORT/"
for _ in $(seq 1 60); do
  if curl -fsS --max-time 2 "$base_url" > "$EVIDENCE_DIR/root.html"; then
    break
  fi
  sleep 1
done

curl -fsS --max-time 5 "$base_url" > "$EVIDENCE_DIR/root.html" || fail "Juice Shop did not become healthy at $base_url"
if ! grep -Eiq "juice|owasp|app-root|<title" "$EVIDENCE_DIR/root.html"; then
  fail "Juice Shop root response did not contain expected application markers"
fi

"${container_cmd[@]}" inspect "$CONTAINER_NAME" > "$EVIDENCE_DIR/container-inspect.json"
"${container_cmd[@]}" ps --filter "name=$CONTAINER_NAME" --format '{{json .}}' > "$EVIDENCE_DIR/container-ps.jsonl"
"${container_cmd[@]}" port "$CONTAINER_NAME" > "$EVIDENCE_DIR/container-port.txt"

if ! grep -Eq "3000/tcp[[:space:]]*->[[:space:]]*$HOST:$PORT" "$EVIDENCE_DIR/container-port.txt"; then
  cat "$EVIDENCE_DIR/container-port.txt"
  fail "container is not bound exactly to $HOST:$PORT"
fi

mounts="$("${container_cmd[@]}" inspect --format '{{json .Mounts}}' "$CONTAINER_NAME")"
echo "$mounts" > "$EVIDENCE_DIR/container-mounts.json"
if [ "$mounts" != "[]" ] && [ "$mounts" != "null" ]; then
  fail "persistent or host mounts are not allowed for clean benchmark state"
fi

if command -v ss >/dev/null 2>&1; then
  ss -ltnp "( sport = :$PORT )" > "$EVIDENCE_DIR/listeners.txt" 2>&1 || true
  cat "$EVIDENCE_DIR/listeners.txt"
fi

cat > "$EVIDENCE_DIR/juice-shop-local-state.json" <<EOF_STATE
{
  "target_alias": "local-juice-shop",
  "base_url": "$base_url",
  "image": "$IMAGE",
  "container_name": "$CONTAINER_NAME",
  "container_id": "$container_id",
  "container_style": "$container_style",
  "network_exposure": "loopback-only",
  "host_binding": "$HOST:$PORT:3000",
  "fresh_container_started": true,
  "persistent_storage_allowed": false,
  "reset_required_before_campaign": true,
  "health_check": "passed"
}
EOF_STATE

find "$EVIDENCE_DIR" -type f -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE_DIR/SHA256SUMS" 2>/dev/null || true

echo "juice_shop_reset_status=0"
echo "container_style=$container_style"
echo "base_url=$base_url"
echo "evidence_dir=$EVIDENCE_DIR"
