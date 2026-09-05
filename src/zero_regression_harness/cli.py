# SPDX-License-Identifier: Apache-2.0
"""Console entry for the Zero-Regression harness."""
from __future__ import annotations

import argparse
from pathlib import Path

from .certify import certify
from .evidence import verify_log


def verify_command(log: Path) -> int:
    errors, summary = verify_log(log)
    if errors:
        print(errors[0])
        return 1
    print(f"OK: {log} ({summary['records']} records; certificate derives from chain)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zero-regression",
        description="Zero-Regression certification harness",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify_parser = sub.add_parser("verify", help="verify an evidence.jsonl chain without running tests or mutmut")
    verify_parser.add_argument("log", type=Path, help="evidence.jsonl to verify")

    certify_parser = sub.add_parser("certify", help="run the five-stage certification protocol")
    certify_parser.add_argument("subject", type=Path)

    args = parser.parse_args(argv)
    if args.command == "verify":
        return verify_command(args.log)
    certify(args.subject)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
