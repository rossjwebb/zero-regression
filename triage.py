#!/usr/bin/env python3
"""Append human survivor decisions or signed overrides to an evidence chain."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from zero_regression_harness.triage import add_override, set_class, show_queue  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="evidence run directory")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    set_parser = sub.add_parser("set")
    set_parser.add_argument("mutant_id")
    set_parser.add_argument("classification", choices=["EQUIVALENT", "GAP_REMEDIATED", "UNDER_INVESTIGATION"])
    override = sub.add_parser("override")
    override.add_argument("mutant_id")
    override.add_argument("--name", required=True)
    override.add_argument("--reason-code", required=True)
    override.add_argument("--justification", required=True)
    args = parser.parse_args()
    if args.command == "list":
        print(show_queue(args.run), end="")
    elif args.command == "set":
        set_class(args.run, args.mutant_id, args.classification)
    else:
        add_override(args.run, args.mutant_id, args.name, args.reason_code, args.justification)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
