#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Write a score-free receipt from a live run-pit.sh work tree.

Never copies pit.log or the HTML report body. Those files contain
PIT's own kill counts. This script records process facts only:
executed or blocked=, pin identities, judge outcome, HTML present
and gitignored. mutation_score stays not-stored.

This is not a paper execution of S2.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

SUBJECT = Path(__file__).resolve().parent
REPO = SUBJECT.parent.parent
WORK = SUBJECT / "work"
OUT = SUBJECT / "evidence" / "pit-receipt.json"

if str(SUBJECT) not in sys.path:
    sys.path.insert(0, str(SUBJECT))

from toolchain import (  # noqa: E402
    build_live_receipt,
    contains_forbidden_score_text,
    load_pins,
    receipt_score_errors,
)


def fail(message: str, extra: str = "") -> int:
    print(f"S2 FAIL-CLOSED: {message}", file=sys.stderr)
    if extra:
        print(extra, file=sys.stderr, end="" if extra.endswith("\n") else "\n")
    return 2


def html_report_tracked() -> bool:
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "subjects/commons-csv/work/pit-reports/index.html"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return tracked.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a score-free S2 PIT receipt")
    parser.add_argument(
        "--pit-exit",
        type=int,
        default=None,
        help="run-pit.sh process exit code if known (omit to infer from work/)",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="print JSON to stdout instead of writing evidence/pit-receipt.json",
    )
    args = parser.parse_args()

    pins = load_pins()
    python_version = platform.python_version()
    receipt = build_live_receipt(
        pins=pins,
        work=WORK,
        python_version=python_version,
        pit_rc=args.pit_exit,
        html_report_tracked=html_report_tracked(),
    )
    errors = receipt_score_errors(receipt)
    dumped = json.dumps(receipt, indent=2, sort_keys=False) + "\n"
    if contains_forbidden_score_text(dumped):
        errors.append("serialized receipt stores a mutation-score claim")
    if receipt.get("html_report_tracked") is True:
        errors.append("HTML report must not be a git object")
    if receipt.get("html_report_body_stored") is not False:
        errors.append("HTML body must not be stored")
    if receipt.get("pit_log_body_stored") is not False:
        errors.append("pit.log body must not be stored")
    if errors:
        return fail("receipt is not score-free", extra="\n".join(f"  {e}" for e in errors))

    if args.stdout_only:
        sys.stdout.write(dumped)
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(dumped, encoding="utf-8")
        print(
            "S2 PIT RECEIPT "
            f"mutation_score=not-stored "
            f"paper_s2=unexecuted "
            f"status={receipt['status']} "
            f"executed={str(receipt['executed']).lower()} "
            f"path={OUT.relative_to(REPO)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
