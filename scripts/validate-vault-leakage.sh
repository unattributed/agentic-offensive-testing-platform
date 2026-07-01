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

bad_paths=$(printf '%s\n' "$files" | grep -E '(^|/)(vault|sensitive-vault|sensitive_annex|poc-workspace)/(ciphertext|metadata|logs)/|(^|/)sensitive-annex-.*\.plaintext(\.|$)|(^|/)vault-raw-|(^|/)raw-vault-' || true)
if [ -n "$bad_paths" ]; then
  echo "vault leakage validation failed: prohibited sensitive vault paths are tracked"
  echo "$bad_paths"
  exit 1
fi

scan_files=$(printf '%s\n' "$files" | grep -Ev '^(scripts/(validate-vault-leakage|validate-repository-safety)\.sh|tests/test_vault_leakage_script\.py)$' || true)
if [ -n "$scan_files" ]; then
  findings=$(printf '%s\n' "$scan_files" | xargs grep -niE 'vault_plaintext[[:space:]]*[:=]|raw_vault_material[[:space:]]*[:=]|unencrypted_sensitive_annex[[:space:]]*[:=]' 2>/dev/null || true)
  if [ -n "$findings" ]; then
    echo "vault leakage validation failed: plaintext vault marker found"
    echo "$findings"
    exit 1
  fi
fi

echo "vault leakage validation passed"
