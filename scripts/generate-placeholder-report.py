#!/usr/bin/env python3
"""Write the deterministic evaluator placeholder report."""

from __future__ import annotations

import argparse
from pathlib import Path

from aotp.demo_release import generate_placeholder_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generate_placeholder_report(), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
