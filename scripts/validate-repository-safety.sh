#!/usr/bin/env sh
set -eu

root=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
cd "$root"

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  files=$(git ls-files)
else
  files=$(find . \
    \( -type d \( \
      -name .git -o \
      -name .pytest_cache -o \
      -name __pycache__ -o \
      -name .venv -o \
      -name build -o \
      -name dist -o \
      -name '*.egg-info' -o \
      -name .aotp \
    \) -prune \) -o \
    \( -type f ! -name '*.pyc' -print \) |
    sed 's#^\./##')
fi

bad_names=$(printf '%s\n' "$files" | grep -E '(^|/)(private|evidence|screenshots|traces)/|(^|/)\.env$|\.har$|\.pem$|\.key$|\.p12$' || true)
if [ -n "$bad_names" ]; then
  echo "repository safety failed: prohibited tracked paths"
  echo "$bad_names"
  exit 1
fi

scan_files=$(printf '%s\n' "$files" | grep -Ev '^(scripts/(validate-repository-safety|audit-repository-release)\.sh|tests/(test_redaction|test_repository_safety)\.py)$' || true)
if [ -n "$scan_files" ]; then
  findings=$(printf '%s\n' "$scan_files" | xargs grep -niE \
    '(AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|authorization:[[:space:]]*bearer[[:space:]]+[A-Za-z0-9._~+/=-]{8,}|cookie:[[:space:]]*[^[:space:]]+|session[_-]?id[[:space:]]*[:=][[:space:]]*[A-Za-z0-9._~+/=-]{8,})' 2>/dev/null || true)
  if [ -n "$findings" ]; then
    echo "repository safety failed: likely secret or private evidence"
    echo "$findings"
    exit 1
  fi
fi

if [ -x "scripts/validate-vault-leakage.sh" ]; then
  scripts/validate-vault-leakage.sh
fi

echo "repository safety validation passed"
