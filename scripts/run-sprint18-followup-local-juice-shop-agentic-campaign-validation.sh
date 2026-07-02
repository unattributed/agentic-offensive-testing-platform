#!/usr/bin/env bash
set -Eeuo pipefail

REPO=""
EVIDENCE_DIR=""
LIVE_CAMPAIGN="0"
PORT="3000"

usage() {
  cat <<'EOF'
Usage: scripts/run-sprint18-followup-local-juice-shop-agentic-campaign-validation.sh --repo DIR --evidence-dir DIR [options]

Validate the Sprint 18 follow-up local Juice Shop agentic campaign runner.
By default this runs focused, network-silent unit tests. Use --live-campaign
when intentionally resetting and testing the local Juice Shop container.

Options:
  --repo DIR          Repository root
  --evidence-dir DIR  Evidence output directory
  --live-campaign     Reset local Juice Shop and run the live bounded campaign
  --port PORT         Local Juice Shop host port, default 3000
  -h, --help          Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --live-campaign) LIVE_CAMPAIGN="1"; shift ;;
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
PYTHON="$REPO/.venv/bin/python"
test -x "$PYTHON"

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo=$REPO"
  echo "evidence_dir=$EVIDENCE_DIR"
  echo "live_campaign=$LIVE_CAMPAIGN"
  echo "port=$PORT"
  echo "python=$PYTHON"
  "$PYTHON" --version
  echo "git_head=$(git rev-parse HEAD 2>/dev/null || true)"
  echo "git_branch=$(git branch --show-current 2>/dev/null || true)"
  git status --short 2>/dev/null || true
} | tee "$EVIDENCE_DIR/inventory.txt"

PYTHONPATH=src "$PYTHON" -m pytest \
  tests/test_juice_shop_agentic_campaign.py \
  tests/test_juice_shop_agentic_campaign_scripts.py \
  tests/test_juice_shop_local_profile.py \
  tests/test_juice_shop_benchmark_mapping.py

if [ "$LIVE_CAMPAIGN" = "1" ]; then
  scripts/run-local-juice-shop-agentic-campaign.sh \
    --repo "$REPO" \
    --evidence-dir "$EVIDENCE_DIR/live-campaign" \
    --port "$PORT"
fi

sha256sum "$EVIDENCE_DIR"/* > "$EVIDENCE_DIR/SHA256SUMS" 2>/dev/null || true

echo "sprint18_followup_juice_shop_agentic_campaign_status=0"
echo "log=$LOG"
