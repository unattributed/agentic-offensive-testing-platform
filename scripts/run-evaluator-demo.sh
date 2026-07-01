#!/usr/bin/env sh
set -eu

root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
python=${AOTP_DEMO_PYTHON:-"$root/.venv/bin/python"}
if [ ! -x "$python" ]; then
  echo "demo failed: set AOTP_DEMO_PYTHON to a Python with project dependencies" >&2
  exit 2
fi
if [ "$#" -gt 1 ]; then
  echo "usage: $0 [empty-workspace]" >&2
  exit 2
fi

temporary=false
if [ "$#" -eq 1 ]; then
  workspace=$1
  mkdir -p "$workspace"
else
  workspace=$(mktemp -d "${TMPDIR:-/tmp}/aotp-demo.XXXXXXXX")
  temporary=true
fi
workspace=$(CDPATH= cd -- "$workspace" && pwd)
if [ -e "$workspace/.aotp" ]; then
  echo "demo failed: workspace already contains .aotp state" >&2
  exit 2
fi
output="$workspace/.aotp/demo"
mkdir -p "$output"

run_cli() {
  PYTHONPATH="$root/src" "$python" -m aotp.cli "$@"
}

cd "$workspace"
run_cli validate-config \
  --scope "$root/config/scope.example.yaml" \
  >"$output/validate-config.json"
run_cli list-modules >"$output/modules.json"
run_cli list-cases >"$output/cases.json"
run_cli dry-run \
  --scope "$root/config/scope.example.yaml" \
  >"$output/dry-run.json"
run_cli campaign-plan \
  --scope "$root/config/scope.example.yaml" \
  --campaign "$root/campaigns/authorized-webapp-campaign.example.yaml" \
  >"$output/campaign-plan.json"
run_cli campaign-run \
  --scope "$root/config/scope.example.yaml" \
  --campaign "$root/campaigns/authorized-webapp-campaign.example.yaml" \
  >"$output/campaign-run.json"

state_path=$(
  "$python" -c \
    'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["state"])' \
    "$output/campaign-run.json"
)
run_cli campaign-events-verify --state "$state_path" >"$output/events-verify.json"
run_cli campaign-report --state "$state_path" >"$output/placeholder-report.md"

"$python" - "$state_path" "$output/placeholder-report.md" "$output/summary.json" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["state"]
report = Path(sys.argv[2]).read_text(encoding="utf-8")
summary = {
    "campaign_id": state["campaign_id"],
    "completed_objectives": state["completed_modules"],
    "demonstration_data": "placeholder_only",
    "evidence_records": len(state["evidence_directories"]),
    "network_mode": "network_silent",
    "report_limitations_declared": "does not infer vulnerabilities" in report,
    "report_ready_findings": 0,
    "request_count": state["request_counters"]["total"],
    "schema_version": "1.0",
    "status": state["current_status"],
}
Path(sys.argv[3]).write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

cat "$output/summary.json"
echo "demo artifacts: $output"
if [ "$temporary" = true ]; then
  echo "temporary workspace retained for this process: $workspace"
fi
