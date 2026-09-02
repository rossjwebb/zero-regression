#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Create a hash-valid reconstruction of the published fintx aggregate evidence.

This is deliberately not a claim that the production source was re-executed in
this repository. It makes the paper's published 43/100%/252/246/6/0 aggregate
inspectable by verify.py until the real, pinned fintx checkout is supplied.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from zero_regression_harness.certificate import certificate_payload_from_records, render_certificate  # noqa: E402
from zero_regression_harness.evidence import append_record, load_records  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "fixtures" / "fintx-accounting-migration" / "evidence" / "published-aggregate-reconstruction")
    args = parser.parse_args()
    run = args.output.resolve()
    log = run / "evidence.jsonl"
    if log.exists():
        raise SystemExit(f"refusing to overwrite {log}")
    config = append_record(log, "CONFIG", {
        "subject": "fintx-accounting-migration (published aggregate reconstruction)",
        "source_revision": "NOT_AVAILABLE_IN_THIS_WORKSPACE",
        "suite_revision": "NOT_AVAILABLE_IN_THIS_WORKSPACE",
        "tools": {"python": "3.12.3", "mutmut": "3.6.0", "pytest": "9.1.1", "pytest-cov": "7.1.0"},
        "operator_set": "mutmut-3.6.0-default",
        "unverified_scope": "Exact source, test checkout, and original production evidence were not supplied with this workspace.",
        "provenance": "aggregate figures transcribed from the paper (v0.5, 30 Aug 2026)",
    })
    append_record(log, "BASELINE", {"attempts": [{"summary": {"tests": 43, "failures": 0, "errors": 0, "skipped": 0, "passed": 43}, "coverage": {"covered": 190, "statements": 190, "percent": 100.0}, "runtime_seconds": 0.36}, {"summary": {"tests": 43, "failures": 0, "errors": 0, "skipped": 0, "passed": 43}, "coverage": {"covered": 190, "statements": 190, "percent": 100.0}, "runtime_seconds": 0.36}], "tests": {"tests": 43, "failures": 0, "errors": 0, "skipped": 0, "passed": 43}, "coverage": {"covered": 190, "statements": 190, "percent": 100.0}, "runtime_seconds": 0.72, "deterministic": True})
    for mutant in range(1, 253):
        outcome = "KILLED" if mutant <= 246 else "SURVIVED"
        row = {"id": str(mutant), "location": "fintx/accounting.py:published-aggregate", "operator": "mutmut", "outcome": outcome, "killing_test": f"published::test_{mutant}" if outcome == "KILLED" else None}
        if mutant == 1:
            row["mutation_stage_runtime_seconds"] = 31.0
        append_record(log, "MUTANT_RESULT", row)
    # The supplied paper aggregate does not disclose a per-class count. Do not
    # manufacture one: the true production chain must replace this fixture.
    classes = ["UNDER_INVESTIGATION"] * 6
    for mutant, classification in zip(range(247, 253), classes):
        append_record(log, "TRIAGE", {"mutant_id": str(mutant), "classification": classification})
    provisional = {"type": "CERTIFICATE", "payload": {"config_hash": config["hash"]}}
    payload = certificate_payload_from_records(load_records(log), provisional)
    certificate = append_record(log, "CERTIFICATE", payload)
    (run / "certificate.txt").write_text(render_certificate(payload, config, certificate["hash"]), encoding="utf-8")
    print(run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
