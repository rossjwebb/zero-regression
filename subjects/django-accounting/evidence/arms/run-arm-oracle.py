#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the S1 replay-only oracle and print a JSON receipt.

This is the shared Part B arm probe. It does not write arm.json, does
not store a mutation score, and does not claim paper S1. A 27/0
receipt means the 27 recorded traces still replay. That is not a
proof of accounting correctness and is not clean-generator success.
"""
from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
from pathlib import Path

ARMS = Path(__file__).resolve().parent
SUBJECT = ARMS.parent.parent
REPO = SUBJECT.parent.parent
ORACLE = SUBJECT / "oracle.py"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_ORACLE = f"ORACLE OK pin={PIN} cases=27 replay-only"
CASE_LINE = re.compile(r"^  case ", re.M)


def python_version() -> str:
    return platform.python_version()


def run_oracle() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ORACLE)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def counts(code: int, stdout: str, stderr: str) -> tuple[int, int]:
    observed = stdout.rstrip("\n")
    if code == 0 and observed == EXPECTED_ORACLE:
        return 27, 0
    mismatched = len(CASE_LINE.findall(stderr))
    return 27 - mismatched, mismatched


def receipt() -> dict:
    completed = run_oracle()
    stdout = completed.stdout
    stderr = completed.stderr
    match_count, mismatch_count = counts(completed.returncode, stdout, stderr)
    observed = stdout.rstrip("\n")
    return {
        "kind": "s1-part-b-oracle-receipt",
        "command": "python3.12 subjects/django-accounting/oracle.py",
        "python": python_version(),
        "exit": completed.returncode,
        "stdout": observed,
        "stderr": stderr,
        "match_count": match_count,
        "mismatch_count": mismatch_count,
        "pin": PIN,
        "oracle": "replay-only",
        "recorded_traces": 27,
        "domain_correctness": "out_of_scope",
        "paper_s1": "unexecuted",
        "mutation_score": "not-stored",
        "zero_mismatch_means": "oracle too thin to discriminate",
        "zero_mismatch_does_not_mean": [
            "four clean generators",
            "success theatre",
            "paper S1",
        ],
    }


def main() -> int:
    payload = receipt()
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    if payload["exit"] != 0 or payload["stdout"] != EXPECTED_ORACLE:
        print(
            "S1 PART B ARM RECEIPT: oracle stdout was not the required replay-only OK line",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
