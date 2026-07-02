#!/usr/bin/env bash
set -Eeuo pipefail

REPO=""
EVIDENCE_DIR=""
APPLY="false"

usage() {
  cat <<'EOF'
Usage:
  run-sprint18-wstg-engine-correction.sh --repo PATH --evidence-dir PATH --apply

Validates the corrected Sprint 18 WSTG engine foundation using the repository's
local Python environment. It does not run live offensive tests.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="${2:-}"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    --apply) APPLY="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$REPO" || -z "$EVIDENCE_DIR" ]]; then
  usage >&2
  exit 2
fi
if [[ "$APPLY" != "true" ]]; then
  echo "Refusing to run without --apply" >&2
  exit 2
fi
if [[ ! -d "$REPO/src/aotp" || ! -d "$REPO/tests" ]]; then
  echo "repo does not look like agentic-offensive-testing-platform: $REPO" >&2
  exit 2
fi

mkdir -p "$EVIDENCE_DIR"
LOG="$EVIDENCE_DIR/run.log"
SUMMARY="$EVIDENCE_DIR/summary.txt"

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo=$REPO"
  echo "evidence_dir=$EVIDENCE_DIR"
  echo
  cd "$REPO"
  echo "git_head=$(git rev-parse HEAD 2>/dev/null || true)"
  echo "git_branch=$(git branch --show-current 2>/dev/null || true)"
  echo
  if [[ -x ".venv/bin/python" ]]; then
    PY=".venv/bin/python"
  else
    PY="$(command -v python3)"
  fi
  echo "python=$PY"
  "$PY" --version
  echo
  export PYTHONPATH="$REPO/src"
  "$PY" -m pytest \
    tests/test_wstg_catalog_v42.py \
    tests/test_wstg_engine_plan.py \
    tests/test_wstg_engine_no_target_specific_dependencies.py \
    tests/test_wstg_strategy_map.py \
    tests/test_wstg_objective_generator.py \
    tests/test_wstg_coverage.py \
    tests/test_wstg_execution_adapter.py
} 2>&1 | tee "$LOG"

status=${PIPESTATUS[0]}
{
  echo "sprint18_wstg_engine_correction_status=$status"
  echo "log=$LOG"
} | tee "$SUMMARY"

tar -C "$(dirname "$EVIDENCE_DIR")" -czf "$EVIDENCE_DIR.tar.gz" "$(basename "$EVIDENCE_DIR")"
sha256sum "$EVIDENCE_DIR.tar.gz" > "$EVIDENCE_DIR.tar.gz.sha256"
exit "$status"
