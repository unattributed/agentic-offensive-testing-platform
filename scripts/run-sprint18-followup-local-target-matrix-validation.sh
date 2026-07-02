#!/usr/bin/env bash
set -euo pipefail

REPO=""
EVIDENCE_DIR=""
LIVE_CRAPI=0
INSTALL_COMPOSE_IF_MISSING=0

usage() {
  cat <<'USAGE'
Usage: scripts/run-sprint18-followup-local-target-matrix-validation.sh --repo PATH --evidence-dir PATH [--live-crapi] [--install-compose-if-missing]
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --live-crapi) LIVE_CRAPI=1; shift ;;
    --install-compose-if-missing) INSTALL_COMPOSE_IF_MISSING=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$REPO" ] || { echo "--repo is required" >&2; exit 2; }
[ -n "$EVIDENCE_DIR" ] || { echo "--evidence-dir is required" >&2; exit 2; }
mkdir -p "$EVIDENCE_DIR"

cd "$REPO"
PYTHON="$REPO/.venv/bin/python"
test -x "$PYTHON" || { echo "expected project venv python at $PYTHON" >&2; exit 1; }

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo=$REPO"
  echo "evidence_dir=$EVIDENCE_DIR"
  echo "live_crapi=$LIVE_CRAPI"
  echo "install_compose_if_missing=$INSTALL_COMPOSE_IF_MISSING"
  echo "python=$PYTHON"
  "$PYTHON" --version
  echo "git_head=$(git rev-parse HEAD 2>/dev/null || true)"
  echo "git_branch=$(git branch --show-current 2>/dev/null || true)"
  git status --short || true
  echo
  PYTHONPATH=src "$PYTHON" -m pytest \
    tests/test_local_target_registry.py \
    tests/test_crapi_local_profile.py \
    tests/test_crapi_benchmark_mapping.py \
    tests/test_local_target_matrix_scripts.py \
    tests/test_development_plan_local_target_matrix.py
} 2>&1 | tee "$EVIDENCE_DIR/run.log"

if [ "$LIVE_CRAPI" = "1" ]; then
  echo "error: --live-crapi is pending_unsupported in Sprint 18H; use Juice Shop for proven live local target validation" | tee "$EVIDENCE_DIR/live-crapi.log" >&2
  "$REPO/scripts/install-local-target-matrix.sh" \
    --repo "$REPO" \
    --target crapi \
    --evidence-dir "$EVIDENCE_DIR/live-crapi" \
    --live 2>&1 | tee -a "$EVIDENCE_DIR/live-crapi.log"
fi

find "$EVIDENCE_DIR" -type f -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE_DIR/SHA256SUMS" 2>/dev/null || true

echo "sprint18_followup_local_target_matrix_status=0"
echo "log=$EVIDENCE_DIR/run.log"
