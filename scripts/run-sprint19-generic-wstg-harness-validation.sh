#!/usr/bin/env bash
set -euo pipefail

REPO=""
EVIDENCE_DIR=""
FULL=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --full) FULL=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$REPO" ] || [ -z "$EVIDENCE_DIR" ]; then
  echo "usage: $0 --repo <path> --evidence-dir <path> [--full]" >&2
  exit 2
fi

cd "$REPO"
mkdir -p "$EVIDENCE_DIR"
LOG="$EVIDENCE_DIR/run.log"
PYTHON="$REPO/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3)"
fi

{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo=$REPO"
  echo "evidence_dir=$EVIDENCE_DIR"
  echo "full=$FULL"
  echo "python=$PYTHON"
  "$PYTHON" --version
  echo "git_head=$(git rev-parse HEAD)"
  echo "git_branch=$(git branch --show-current)"
  git status --short
  echo
  echo "focused sprint 19 tests"
  PYTHONPATH=src "$PYTHON" -m pytest \
    tests/test_target_runtime_contract.py \
    tests/test_execution_planner.py \
    tests/test_proof_requests.py \
    tests/test_wstg_live_campaign.py
  echo
  echo "compileall"
  "$PYTHON" -m compileall src tests
  echo
  echo "git_diff_check"
  git diff --check
  if [ "$FULL" -eq 1 ]; then
    echo
    echo "full test suite"
    PYTHONPATH=src "$PYTHON" -m pytest
  fi
} | tee "$LOG"

tar -C "$(dirname "$EVIDENCE_DIR")" -czf "$EVIDENCE_DIR.tar.gz" "$(basename "$EVIDENCE_DIR")"
sha256sum "$EVIDENCE_DIR.tar.gz" | tee "$EVIDENCE_DIR.tar.gz.sha256"
