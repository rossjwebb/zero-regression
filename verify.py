#!/usr/bin/env python3
"""Verify a Zero-Regression evidence chain without running tests or mutmut."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from zero_regression_harness.evidence import verify_log  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="evidence.jsonl to verify")
    args = parser.parse_args()
    errors, summary = verify_log(args.log)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"OK: {args.log} ({summary['records']} records; certificate derives from chain)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
