#!/usr/bin/env bash
set -Eeuo pipefail

REPO=""
EVIDENCE_DIR=""
PORT="3000"
RESET="1"
MAX_REQUESTS="12"
MAX_READY_TESTS="30"
CAMPAIGN_ID="local-juice-shop-agentic-campaign"

usage() {
  cat <<'EOF'
Usage: scripts/run-local-juice-shop-agentic-campaign.sh --repo DIR --evidence-dir DIR [options]

Reset local OWASP Juice Shop and run the bounded AOTP agentic benchmark
campaign using the repository Python virtual environment.

Options:
  --repo DIR             Repository root
  --evidence-dir DIR     Evidence output directory
  --port PORT            Local Juice Shop host port, default 3000
  --no-reset             Do not reset Juice Shop before the campaign
  --max-requests N       Maximum safe GET requests, default 12
  --max-ready-tests N    Maximum ready WSTG plan entries, default 30
  --campaign-id ID       Campaign identifier
  -h, --help             Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --no-reset) RESET="0"; shift ;;
    --max-requests) MAX_REQUESTS="$2"; shift 2 ;;
    --max-ready-tests) MAX_READY_TESTS="$2"; shift 2 ;;
    --campaign-id) CAMPAIGN_ID="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$REPO" ] || { usage >&2; exit 2; }
[ -n "$EVIDENCE_DIR" ] || { usage >&2; exit 2; }

mkdir -p "$EVIDENCE_DIR"
LOG="$EVIDENCE_DIR/run-local-juice-shop-agentic-campaign.log"
exec > >(tee -a "$LOG") 2>&1

cd "$REPO"
PYTHON="$REPO/.venv/bin/python"
test -x "$PYTHON"

case "$PORT" in
  ''|*[!0-9]*) echo "error=port must be numeric" >&2; exit 2 ;;
esac
if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
  echo "error=port must be between 1024 and 65535" >&2
  exit 2
fi

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo=$REPO"
  echo "evidence_dir=$EVIDENCE_DIR"
  echo "campaign_id=$CAMPAIGN_ID"
  echo "port=$PORT"
  echo "reset=$RESET"
  echo "python=$PYTHON"
  "$PYTHON" --version
  echo "git_head=$(git rev-parse HEAD 2>/dev/null || true)"
  echo "git_branch=$(git branch --show-current 2>/dev/null || true)"
  git status --short 2>/dev/null || true
} | tee "$EVIDENCE_DIR/inventory.txt"

if [ "$RESET" = "1" ]; then
  scripts/juice-shop-local-reset.sh \
    --evidence-dir "$EVIDENCE_DIR/reset" \
    --port "$PORT"
fi

curl -fsS --max-time 5 "http://127.0.0.1:$PORT/" > "$EVIDENCE_DIR/pre-campaign-root.html"

PYTHONPATH=src "$PYTHON" -m aotp.campaigns.juice_shop_campaign \
  --evidence-dir "$EVIDENCE_DIR/campaign" \
  --base-url "http://127.0.0.1:$PORT/" \
  --campaign-id "$CAMPAIGN_ID" \
  --max-requests "$MAX_REQUESTS" \
  --max-ready-tests "$MAX_READY_TESTS" \
  > "$EVIDENCE_DIR/campaign-result.stdout.json"

sha256sum "$EVIDENCE_DIR"/* > "$EVIDENCE_DIR/SHA256SUMS" 2>/dev/null || true

echo "local_juice_shop_agentic_campaign_status=0"
echo "base_url=http://127.0.0.1:$PORT/"
echo "campaign_evidence_dir=$EVIDENCE_DIR/campaign"
echo "log=$LOG"
