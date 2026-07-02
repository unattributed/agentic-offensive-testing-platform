#!/usr/bin/env bash
set -u -o pipefail

PYTHON_BIN="${AOTP_PYTHON:-}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
EVIDENCE_DIR="${1:-$REPO/.validation-evidence/sprint18-authenticated-osmap-clearbox-$(date -u +%Y%m%d-%H%M%SZ)}"
SKIP_LOCAL_TOOL_CHECKS="${AOTP_SKIP_LOCAL_TOOL_CHECKS:-0}"
FAILURES=0

mkdir -p "$EVIDENCE_DIR"
EVIDENCE_DIR="$(cd "$EVIDENCE_DIR" && pwd)"
LOG="$EVIDENCE_DIR/run.log"
SUMMARY="$EVIDENCE_DIR/summary.txt"
: > "$LOG"
: > "$SUMMARY"

run_required() {
  name="$1"
  shift
  echo "==== $name ====" | tee -a "$LOG"
  "$@" >> "$LOG" 2>&1
  status=$?
  echo "status=$status" | tee -a "$LOG"
  echo "$name status=$status" >> "$SUMMARY"
  if [ "$status" -ne 0 ]; then
    FAILURES=$((FAILURES + 1))
  fi
  return 0
}

run_optional() {
  name="$1"
  shift
  echo "==== $name ====" | tee -a "$LOG"
  "$@" >> "$LOG" 2>&1
  status=$?
  echo "status=$status" | tee -a "$LOG"
  echo "$name status=$status" >> "$SUMMARY"
  return 0
}

if [ -z "$PYTHON_BIN" ]; then
  PYTHON_BIN="$REPO/.venv/bin/python"
fi

{
  date -u
  echo "repo=$REPO"
  echo "python=$PYTHON_BIN"
  echo "skip_local_tool_checks=$SKIP_LOCAL_TOOL_CHECKS"
} | tee -a "$LOG"

cd "$REPO" || exit 2

if [ ! -x "$PYTHON_BIN" ]; then
  echo "missing executable repo virtualenv python: $PYTHON_BIN" | tee -a "$LOG"
  echo "selected_python status=missing_repo_virtualenv" >> "$SUMMARY"
  exit 2
fi

run_optional preflight_git git status --short
run_optional preflight_head git rev-parse HEAD
run_optional preflight_branch git branch --show-current
run_required selected_python_version "$PYTHON_BIN" --version

if [ "$SKIP_LOCAL_TOOL_CHECKS" != "1" ]; then
  run_required validation_python_dependency_imports bash -lc "$(printf '%q' "$PYTHON_BIN") - <<'PY'
import importlib
modules = [
    'deepagents',
    'langchain',
    'langchain_ollama',
    'langgraph',
    'langgraph.checkpoint.sqlite',
    'pip_audit',
    'piplicenses',
]
for module in modules:
    imported = importlib.import_module(module)
    version = getattr(imported, '__version__', 'unknown')
    print(f'{module} import ok version={version}')
PY"
  run_required local_ollama_tool bash -lc 'command -v ollama && ollama --version'
  run_optional local_ollama_tags bash -lc 'ollama list || true'
fi

run_required compileall "$PYTHON_BIN" -m compileall -q src tests
run_required focused_sprint18_pytest "$PYTHON_BIN" -m pytest \
  tests/test_credential_prompt.py \
  tests/test_auth_session.py \
  tests/test_session_evidence_redaction.py \
  tests/test_osmap_source_review.py \
  tests/test_osmap_route_map.py \
  tests/test_osmap_wstg_mapper.py \
  tests/test_osmap_authenticated_wstg.py
run_required sprint17f_adapter_pytest "$PYTHON_BIN" -m pytest tests/test_wstg_execution_adapter.py
run_required dependency_import_guard_pytest "$PYTHON_BIN" -m pytest \
  tests/test_deep_agent_bootstrap.py \
  tests/test_agentic_campaign_loop.py \
  tests/test_langgraph_orchestration.py \
  tests/test_release_check.py::test_v0_1_fast_release_check_passes
run_required licensing_readiness_pytest "$PYTHON_BIN" -m pytest tests/test_licensing_readiness.py
run_required full_pytest "$PYTHON_BIN" -m pytest
if [ -x ./scripts/validate-repository-safety.sh ]; then
  run_required repository_safety ./scripts/validate-repository-safety.sh
else
  echo "repository_safety status=skipped_missing_script" >> "$SUMMARY"
fi
run_required make_test make PYTHON="$PYTHON_BIN" test
if make -n check >/dev/null 2>&1; then
  run_required make_check make PYTHON="$PYTHON_BIN" check
else
  echo "make_check status=skipped_missing_target" >> "$SUMMARY"
fi
run_required targeted_sensitive_review ./scripts/validate-repository-safety.sh
run_optional final_status git status --short

echo "required_validation_failures=$FAILURES" >> "$SUMMARY"
cd "$EVIDENCE_DIR" || exit 2
ARCHIVE="${EVIDENCE_DIR%/}.tar.gz"
tar -czf "$ARCHIVE" .
sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"
echo "evidence_archive=$ARCHIVE" | tee -a "$LOG"
echo "evidence_sha256=$ARCHIVE.sha256" | tee -a "$LOG"

if [ "$FAILURES" -ne 0 ]; then
  exit 1
fi
