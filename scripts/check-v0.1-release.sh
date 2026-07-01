#!/usr/bin/env sh
set -eu

root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$root"
python=${PYTHON:-"$root/.venv/bin/python"}
if [ ! -x "$python" ]; then
  echo "v0.1 release check failed: project Python is unavailable" >&2
  exit 2
fi
python=$("$python" -c 'import sys; print(sys.executable)')
mode=full
if [ "$#" -eq 1 ] && [ "$1" = "--fast" ]; then
  mode=fast
elif [ "$#" -ne 0 ]; then
  echo "usage: $0 [--fast]" >&2
  exit 2
fi

for required in \
  LICENSE.md \
  SECURITY.md \
  README.md \
  pyproject.toml \
  docs/architecture-authority-review.md \
  docs/dependency-license-inventory.md \
  docs/repository-safety-review-v0.1.md \
  examples/demo/dry-run-summary.example.json \
  examples/demo/placeholder-report.example.md
do
  if [ ! -f "$required" ]; then
    echo "v0.1 release check failed: missing $required" >&2
    exit 1
  fi
done

version=$(
  "$python" -c \
    'import pathlib,tomllib; print(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"])'
)
if [ "$version" != "0.1.0" ]; then
  echo "v0.1 release check failed: project version is $version" >&2
  exit 1
fi

PYTHONPATH="$root/src" "$python" -c 'import aotp, aotp.cli'
if [ "$mode" = full ]; then
  make PYTHON="$python" check
else
  "$python" -m compileall -q src tests
  ./scripts/validate-repository-safety.sh
fi
./scripts/audit-repository-release.sh

temporary=$(mktemp -d "${TMPDIR:-/tmp}/aotp-v0.1-check.XXXXXXXX")
trap 'rm -rf "$temporary"' EXIT HUP INT TERM
AOTP_DEMO_PYTHON="$python" \
  ./scripts/run-evaluator-demo.sh "$temporary/demo" >"$temporary/demo.log"
cmp \
  "$temporary/demo/.aotp/demo/summary.json" \
  examples/demo/dry-run-summary.example.json
PYTHONPATH="$root/src" "$python" scripts/generate-placeholder-report.py \
  --output "$temporary/placeholder-report.md" >"$temporary/report.log"
cmp \
  "$temporary/placeholder-report.md" \
  examples/demo/placeholder-report.example.md

echo "v0.1 release check passed"
echo "version=$version"
echo "validation_mode=$mode"
echo "repository_safety=passed"
echo "history_audit=passed"
echo "demo_summary=matched"
echo "placeholder_report=matched"
