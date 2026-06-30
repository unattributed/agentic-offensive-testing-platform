"""Small CLI dispatcher for Sprint 4 dry-run WSTG contracts.

The dispatcher is intentionally narrow. It handles only the new Sprint 4
registry case identifiers. Existing YAML-backed AOTP CLI behavior remains owned
by src/aotp/cli.py and is reached by returning None.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .capability_registry import list_adapters, module_summary
from .wstg_case_registry import build_dry_run_record, case_summary_rows, get_case


ROOT = Path(__file__).resolve().parents[2]
LEGACY_RUN_CASE_ARGS = {"--live", "--program-profile", "--operator-approved"}


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _legacy_case_files() -> list[str]:
    cases_dir = ROOT / "cases"
    if not cases_dir.is_dir():
        return []
    return sorted(path.name for path in cases_dir.glob("*.yaml"))


def dispatch_sprint4_command(argv: list[str] | None) -> int | None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return None
    command = args[0]
    if command == "list-cases":
        _print_json({"case_files": _legacy_case_files(), "cases": case_summary_rows()})
        return 0
    if command == "list-modules":
        data = module_summary()
        data["legacy_modules"] = [
            "wstg_webapp",
            "service_control_panel",
            "bounded_fuzzing",
            "sbom_review",
            "crypto_controls",
        ]
        data["adapters"] = list_adapters()
        _print_json(data)
        return 0
    if command == "run-case":
        if any(arg in LEGACY_RUN_CASE_ARGS for arg in args[1:]):
            return None
        parser = argparse.ArgumentParser(prog="aotp run-case")
        parser.add_argument("--scope", required=True)
        parser.add_argument("--case", required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--approval", action="append", default=[])
        parsed, unknown = parser.parse_known_args(args[1:])
        if unknown:
            return None
        if not parsed.dry_run:
            return None
        try:
            case = get_case(parsed.case)
        except KeyError:
            return None
        approved = bool(parsed.approval)
        record = build_dry_run_record(case["case_id"], target_alias="example-target", approved=approved)
        _print_json(record)
        return 0 if record["policy_decision"] == "allowed_dry_run" else 2
    return None
