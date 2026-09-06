#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Score-free POSTTRAN job-receipt gate.

This is not paper S3 and does not invent a mutation score.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SUBJECT = Path(__file__).resolve().parent
EVIDENCE = SUBJECT / "evidence"
POSTURE = EVIDENCE / "s3-posture.json"
RECEIPT = EVIDENCE / "job-receipt.json"
ENGLISH = EVIDENCE / "EVIDENCE.md"
WORK_RECEIPT = SUBJECT / "work" / "POSTTRAN"

NUMERIC_SCORE_KEYS = frozenset({"mutation_score", "kill_rate", "killed", "seeded", "survivors"})


def score_errors(node: object, prefix: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{prefix}.{key}" if prefix else key
            if key == "mutation_score" and value not in ("not-stored", "not-recorded", None):
                errors.append(f"{here}: expected not-stored/not-recorded got {value!r}")
            elif key in NUMERIC_SCORE_KEYS and isinstance(value, (int, float)):
                errors.append(f"{here} must not be numeric")
            errors.extend(score_errors(value, here))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            errors.extend(score_errors(item, f"{prefix}[{index}]"))
    return errors


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must be a JSON object")
    return payload


def read_kv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def check_committed() -> list[str]:
    errors: list[str] = []
    try:
        posture = load_json(POSTURE)
        receipt = load_json(RECEIPT)
    except ValueError as exc:
        return [str(exc)]
    required_posture = {
        "paper_s3": "unexecuted",
        "mutation_score": "not-stored",
        "posttran_job": "run",
        "executed_job": True,
        "status": "gnucobol-posttran-fixture-run",
        "runtime": "gnucobol-indexed-bdb-fixture",
        "ibm_vsam": False,
        "ibm_cics": False,
    }
    for key, expected in required_posture.items():
        if posture.get(key) != expected:
            errors.append(f"posture.{key}: expected {expected!r} got {posture.get(key)!r}")
    runner = posture.get("runner") or {}
    if runner.get("posttran_job") != "run":
        errors.append("runner.posttran_job must be run")
    if runner.get("executed_job") is not True:
        errors.append("runner.executed_job must be true")
    if runner.get("runtime") != "gnucobol-indexed-bdb-fixture":
        errors.append("runner.runtime must be gnucobol-indexed-bdb-fixture")
    if runner.get("records_mutation_score") is not False:
        errors.append("runner.records_mutation_score must be false")
    compile_runner = posture.get("compile_runner") or {}
    if compile_runner.get("posttran_job") != "not-run":
        errors.append("compile_runner.posttran_job must stay not-run")
    if compile_runner.get("path") != "subjects/carddemo/run-cobol.sh":
        errors.append("compile_runner.path must remain run-cobol.sh")
    required_receipt = {
        "paper_s3": "unexecuted",
        "mutation_score": "not-stored",
        "posttran_job": "run",
        "runtime": "gnucobol-indexed-bdb-fixture",
        "ibm_vsam": False,
        "ibm_cics": False,
        "ibm_le_cee3abd": "stub",
        "program_return_code": 4,
        "transactions_processed": 2,
        "transactions_rejected": 1,
        "records_mutation_score": False,
        "work_receipt_gitignored": True,
        "work_receipt_body_stored": False,
    }
    for key, expected in required_receipt.items():
        if receipt.get(key) != expected:
            errors.append(f"receipt.{key}: expected {expected!r} got {receipt.get(key)!r}")
    errors.extend(f"posture: {item}" for item in score_errors(posture))
    errors.extend(f"receipt: {item}" for item in score_errors(receipt))
    if not ENGLISH.is_file():
        errors.append(f"missing {ENGLISH}")
    else:
        text = ENGLISH.read_text(encoding="utf-8")
        for needle in (
            "mutation_score=not-stored",
            "paper_s3=unexecuted",
            "posttran_job=run",
            "runtime=gnucobol-indexed-bdb-fixture",
            "executed_job=true",
            "ibm_vsam=false",
            "ibm_cics=false",
        ):
            if needle not in text:
                errors.append(f"EVIDENCE.md missing {needle!r}")
        if "kill rate" in text.lower() or "killed" in text.lower() and "seeded" in text.lower():
            errors.append("EVIDENCE.md must not state a mutation kill count")
        if "paper s3 executed" in text.lower():
            errors.append("EVIDENCE.md must not claim paper S3 executed")
    dumped = json.dumps({"posture": posture, "receipt": receipt}).lower()
    if "kill rate" in dumped or ("killed" in dumped and "seeded" in dumped):
        errors.append("committed S3 pack invented a mutation kill count")
    return errors


def check_live() -> list[str]:
    errors: list[str] = []
    live = read_kv(WORK_RECEIPT)
    if not live:
        return [f"missing live receipt {WORK_RECEIPT}. Skip is not a pass."]
    expected = {
        "posttran_job": "run",
        "runtime": "gnucobol-indexed-bdb-fixture",
        "ibm_vsam": "false",
        "ibm_cics": "false",
        "ibm_le_cee3abd": "stub",
        "program_return_code": "4",
        "transactions_processed": "2",
        "transactions_rejected": "1",
        "paper_s3": "unexecuted",
        "mutation_score": "not-recorded",
        "executed_job": "true",
        "indexed_file_handler": "BDB",
    }
    for key, value in expected.items():
        if live.get(key) != value:
            errors.append(f"work/POSTTRAN {key}: expected {value!r} got {live.get(key)!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify S3 POSTTRAN job evidence")
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="also require work/POSTTRAN from a live run-posttran.sh execution",
    )
    args = parser.parse_args()
    errors = check_committed()
    if args.require_live:
        errors.extend(check_live())
    if errors:
        print("S3 POSTTRAN FAIL-CLOSED: job evidence is not honest", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 2
    extra = "require-live" if args.require_live else "committed-pack"
    print(
        "S3 POSTTRAN EVIDENCE OK "
        f"{extra} "
        "posttran_job=run "
        "runtime=gnucobol-indexed-bdb-fixture "
        "paper_s3=unexecuted "
        "mutation_score=not-stored"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
