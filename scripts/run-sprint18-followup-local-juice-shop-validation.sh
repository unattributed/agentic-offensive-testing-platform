#!/usr/bin/env bash
set -Eeuo pipefail

REPO=""
EVIDENCE_DIR=""
LIVE_JUICE_SHOP="0"
INSTALL_LOCAL_JUICE_SHOP="0"
PORT="3000"

usage() {
  cat <<'EOF'
Usage: scripts/run-sprint18-followup-local-juice-shop-validation.sh --repo DIR --evidence-dir DIR [options]

Validate the Sprint 18 follow-up local Juice Shop benchmark profile. By default
this is a network-silent project validation. Use --install-local-juice-shop or
--live-juice-shop when intentionally preparing the local benchmark container.

Options:
  --repo DIR                    Repository root
  --evidence-dir DIR            Evidence output directory
  --install-local-juice-shop    Inventory/install Docker if needed, pull image, reset container
  --live-juice-shop             Reset and health-check an already installed local container
  --port PORT                   Local host port, default 3000
  -h, --help                    Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --install-local-juice-shop) INSTALL_LOCAL_JUICE_SHOP="1"; shift ;;
    --live-juice-shop) LIVE_JUICE_SHOP="1"; shift ;;
    --port) PORT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$REPO" ] || { usage >&2; exit 2; }
[ -n "$EVIDENCE_DIR" ] || { usage >&2; exit 2; }
mkdir -p "$EVIDENCE_DIR"
LOG="$EVIDENCE_DIR/run.log"
exec > >(tee -a "$LOG") 2>&1

cd "$REPO"

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo=$REPO"
  echo "evidence_dir=$EVIDENCE_DIR"
  echo "install_local_juice_shop=$INSTALL_LOCAL_JUICE_SHOP"
  echo "live_juice_shop=$LIVE_JUICE_SHOP"
  echo "port=$PORT"
  echo
  echo "git_head=$(git rev-parse HEAD 2>/dev/null || true)"
  echo "git_branch=$(git branch --show-current 2>/dev/null || true)"
  echo
  git status --short 2>/dev/null || true
  echo
  for cmd in python3 curl docker sudo; do
    if command -v "$cmd" >/dev/null 2>&1; then
      echo "$cmd=$(command -v "$cmd")"
      "$cmd" --version 2>&1 | head -5 || true
    else
      echo "$cmd=missing"
    fi
  done
} | tee "$EVIDENCE_DIR/inventory.txt"

PYTHON="python3"
if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
fi
"$PYTHON" --version

PYTHONPATH=src "$PYTHON" -m pytest \
  tests/test_juice_shop_local_profile.py \
  tests/test_juice_shop_benchmark_mapping.py \
  tests/test_juice_shop_local_scripts.py

if [ "$INSTALL_LOCAL_JUICE_SHOP" = "1" ]; then
  scripts/install-local-juice-shop-benchmark.sh \
    --evidence-dir "$EVIDENCE_DIR/install" \
    --port "$PORT"
elif [ "$LIVE_JUICE_SHOP" = "1" ]; then
  scripts/juice-shop-local-reset.sh \
    --evidence-dir "$EVIDENCE_DIR/reset" \
    --port "$PORT"
fi

if [ -d "$EVIDENCE_DIR/install" ] || [ -d "$EVIDENCE_DIR/reset" ]; then
  curl -fsS "http://127.0.0.1:$PORT/" > "$EVIDENCE_DIR/live-root.html"
fi

sha256sum "$EVIDENCE_DIR"/* > "$EVIDENCE_DIR/SHA256SUMS" 2>/dev/null || true

echo "sprint18_followup_local_juice_shop_status=0"
echo "log=$LOG"
