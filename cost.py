#!/usr/bin/env python3
"""Optional deterministic COST-record writer for an external generation run."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from zero_regression_harness.evidence import append_record  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="certification evidence run directory")
    parser.add_argument("--role", required=True, choices=["generator", "adjudicator", "executor"])
    parser.add_argument("--tokens", required=True, type=int)
    parser.add_argument("--spend-usd", required=True, type=float)
    parser.add_argument("--reference", required=True, help="external pipeline-run identifier or immutable invoice reference")
    args = parser.parse_args()
    if args.tokens < 0 or args.spend_usd < 0:
        raise SystemExit("tokens and spend must be non-negative")
    append_record(args.run / "evidence.jsonl", "COST", {"role": args.role, "tokens": args.tokens, "spend_usd": args.spend_usd, "reference": args.reference})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
