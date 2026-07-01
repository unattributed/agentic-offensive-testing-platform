#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 --target https://owned.example/ --program alias --target-alias alias --authorization-reference ref --operator-approved [--model name]"
}

target=
program=
target_alias=
authorization_reference=
operator_approved=
model=${AOTP_OLLAMA_MODEL:-gemma4:latest}

while (($#)); do
  case "$1" in
    --target)
      target=${2:?}
      shift 2
      ;;
    --program)
      program=${2:?}
      shift 2
      ;;
    --target-alias)
      target_alias=${2:?}
      shift 2
      ;;
    --authorization-reference)
      authorization_reference=${2:?}
      shift 2
      ;;
    --operator-approved)
      operator_approved=1
      shift
      ;;
    --model)
      model=${2:?}
      shift 2
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$target" || -z "$program" || -z "$target_alias" || -z "$authorization_reference" || -z "$operator_approved" ]]; then
  usage >&2
  exit 2
fi

case "$target" in
  https://*/*) ;;
  *)
    echo "Sprint 14 demo requires an explicitly supplied HTTPS origin ending in /" >&2
    exit 2
    ;;
esac

root=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
python=${AOTP_PYTHON:-"$root/.venv/bin/python"}

"$python" -m aotp.agentic_campaign_loop \
  --target "$target" \
  --program "$program" \
  --target-alias "$target_alias" \
  --authorization-reference "$authorization_reference" \
  --operator-approved \
  --model "$model" \
  --ollama-url http://127.0.0.1:11434 \
  --workspace-root "$root/.aotp/campaigns"
