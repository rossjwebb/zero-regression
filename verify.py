#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify a Zero-Regression evidence chain without running tests or mutmut."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from zero_regression_harness.cli import verify_command  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "log",
        type=Path,
        help="evidence.jsonl chain, or a public S1–S3 subject directory",
    )
    args = parser.parse_args()
    return verify_command(args.log)


if __name__ == "__main__":
    raise SystemExit(main())
