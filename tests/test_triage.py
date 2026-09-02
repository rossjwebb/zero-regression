# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from zero_regression_harness.certificate import certificate_payload_from_records
from zero_regression_harness.evidence import append_record, load_records, verify_log
from zero_regression_harness.triage import add_override


def _seed_run(directory: Path, mutant_ids: list[str]) -> Path:
    run = directory / "run"
    run.mkdir()
    log = run / "evidence.jsonl"
    config = append_record(
        log,
        "CONFIG",
        {"subject": "unit", "source_revision": "a", "suite_revision": "b", "tools": {"python": "3.12.3"}, "operator_set": "unit", "unverified_scope": "none"},
    )
    append_record(
        log,
        "BASELINE",
        {"tests": {"tests": 1, "passed": 1, "failures": 0, "errors": 0, "skipped": 0}, "coverage": {"covered": 1, "statements": 1, "percent": 100.0}, "runtime_seconds": 0.01, "deterministic": True},
    )
    append_record(log, "MUTANT_RESULT", {"id": "1", "location": "x.py:1", "operator": "unit", "outcome": "KILLED", "killing_test": "test_x"})
    queue = []
    for mutant_id in mutant_ids:
        append_record(log, "MUTANT_RESULT", {"id": mutant_id, "location": f"x.py:{mutant_id}", "operator": "unit", "outcome": "SURVIVED", "killing_test": None})
        append_record(log, "TRIAGE", {"mutant_id": mutant_id, "classification": "UNDER_INVESTIGATION"})
        queue.append({"mutant_id": mutant_id, "location": f"x.py:{mutant_id}", "operator": "unit", "classification": "UNDER_INVESTIGATION", "rationale": ""})
    payload = certificate_payload_from_records(load_records(log), {"type": "CERTIFICATE", "payload": {"config_hash": config["hash"]}})
    append_record(log, "CERTIFICATE", payload)
    (run / "survivors.json").write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run


class EquivalentByInspectionTests(unittest.TestCase):
    def test_helper_lands_equivalent_and_rejects_missing_evidence_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = _seed_run(Path(temporary), ["2", "3"])
            add_override(
                run,
                "2",
                "Ross Webb",
                "EQUIVALENT_BY_INSPECTION",
                "Initializer is overwritten before the first read.",
                evidence_ref="subjects/accounting-service/TRIAGE-EVIDENCE.md#update__mutmut_12",
            )
            queue = json.loads((run / "survivors.json").read_text(encoding="utf-8"))
            self.assertEqual(next(item["classification"] for item in queue if item["mutant_id"] == "2"), "EQUIVALENT")
            records = load_records(run / "evidence.jsonl")
            override = next(record for record in reversed(records) if record["type"] == "OVERRIDE" and record["payload"]["mutant_id"] == "2")
            self.assertEqual(override["payload"]["reason_code"], "EQUIVALENT_BY_INSPECTION")
            self.assertEqual(override["payload"]["evidence_ref"], "subjects/accounting-service/TRIAGE-EVIDENCE.md#update__mutmut_12")
            triage = next(record for record in reversed(records) if record["type"] == "TRIAGE" and record["payload"]["mutant_id"] == "2")
            self.assertEqual(triage["payload"]["classification"], "EQUIVALENT")
            errors, _ = verify_log(run / "evidence.jsonl")
            self.assertEqual(errors, [])

            with self.assertRaises(ValueError) as raised:
                add_override(run, "3", "Ross Webb", "EQUIVALENT_BY_INSPECTION", "A zero value is already zero.")
            self.assertIn("evidence_ref", str(raised.exception))
            queue = json.loads((run / "survivors.json").read_text(encoding="utf-8"))
            self.assertEqual(next(item["classification"] for item in queue if item["mutant_id"] == "3"), "UNDER_INVESTIGATION")
            self.assertFalse(any(record["type"] == "OVERRIDE" and record["payload"]["mutant_id"] == "3" for record in load_records(run / "evidence.jsonl")))


if __name__ == "__main__":
    unittest.main()
