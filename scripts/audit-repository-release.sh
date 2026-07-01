#!/usr/bin/env sh
set -eu

root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$root"
if ! command -v git >/dev/null 2>&1 || ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "repository release audit failed: Git worktree required" >&2
  exit 2
fi

./scripts/validate-repository-safety.sh

tracked_files=$(git ls-files | wc -l | tr -d ' ')
history_commits=$(git rev-list --all | wc -l | tr -d ' ')
historical_paths=$(
  git log --all --name-only --format= |
    sed '/^$/d' |
    sort -u |
    wc -l |
    tr -d ' '
)

tracked_symlinks=$(git ls-files -s | awk '$1 == "120000" {print $4}')
if [ -n "$tracked_symlinks" ]; then
  echo "repository release audit failed: tracked symlinks are not allowed"
  echo "$tracked_symlinks"
  exit 1
fi

history_names=$(
  git log --all --name-only --format= |
    sed '/^$/d' |
    sort -u
)
bad_history_names=$(
  printf '%s\n' "$history_names" |
    grep -E '(^|/)(private|evidence|screenshots|traces)/|(^|/)\.env$|\.har$|\.pem$|\.key$|\.p12$' ||
    true
)
if [ -n "$bad_history_names" ]; then
  echo "repository release audit failed: prohibited paths exist in history"
  echo "$bad_history_names"
  exit 1
fi

secret_pattern='(AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|authorization:[[:space:]]*bearer[[:space:]]+[A-Za-z0-9._~+/=-]{8,}|cookie:[[:space:]]*[^[:space:]]+|session[_-]?id[[:space:]]*[:=][[:space:]]*[A-Za-z0-9._~+/=-]{8,})'
for commit in $(git rev-list --all); do
  set +e
  raw_findings=$(git grep -niE "$secret_pattern" "$commit" -- . 2>/dev/null)
  status=$?
  set -e
  if [ "$status" -ne 0 ] && [ "$status" -ne 1 ]; then
    echo "repository release audit failed: unable to inspect commit $commit"
    exit 2
  fi
  findings=$(
    printf '%s\n' "$raw_findings" |
      grep -Ev '^[^:]+:(scripts/(validate-repository-safety|audit-repository-release)\.sh|tests/(test_redaction|test_repository_safety)\.py):' ||
      true
  )
  if [ -n "$findings" ]; then
    echo "repository release audit failed: likely secret found in commit $commit"
    echo "$findings"
    exit 1
  fi
done

echo "repository release audit passed"
echo "tracked_files=$tracked_files"
echo "history_commits=$history_commits"
echo "historical_paths=$historical_paths"
echo "tracked_symlinks=0"
echo "history_secret_findings=0"
