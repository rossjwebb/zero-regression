# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from zero_regression_harness.certificate import certificate_payload_from_records
from zero_regression_harness.evidence import append_record, load_records, verify_log

REPO = Path(__file__).resolve().parents[1]


class EvidenceChainTests(unittest.TestCase):
    def test_chain_and_certificate_are_independently_verifiable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "evidence.jsonl"
            config = append_record(log, "CONFIG", {"subject": "unit", "source_revision": "a", "suite_revision": "b", "tools": {"python": "3.12.3"}, "operator_set": "unit", "unverified_scope": "none"})
            append_record(log, "BASELINE", {"tests": {"tests": 1, "passed": 1, "failures": 0, "errors": 0, "skipped": 0}, "coverage": {"covered": 1, "statements": 1, "percent": 100.0}, "runtime_seconds": 0.01, "deterministic": True})
            append_record(log, "MUTANT_RESULT", {"id": "1", "location": "x.py:1", "operator": "unit", "outcome": "KILLED", "killing_test": "test_x"})
            append_record(log, "MUTANT_RESULT", {"id": "2", "location": "x.py:2", "operator": "unit", "outcome": "SURVIVED", "killing_test": None})
            append_record(log, "TRIAGE", {"mutant_id": "2", "classification": "EQUIVALENT"})
            payload = certificate_payload_from_records(load_records(log), {"type": "CERTIFICATE", "payload": {"config_hash": config["hash"]}})
            append_record(log, "CERTIFICATE", payload)
            errors, _ = verify_log(log)
            self.assertEqual(errors, [])

    def test_tampered_record_is_located(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "evidence.jsonl"
            append_record(log, "CONFIG", {"subject": "unit"})
            log.write_text(log.read_text(encoding="utf-8").replace('"unit"', '"altered"'), encoding="utf-8")
            errors, _ = verify_log(log)
            self.assertTrue(any("seq 1: hash mismatch" in error for error in errors))

    def test_one_byte_mutation_names_the_broken_seq(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "evidence.jsonl"
            config = append_record(log, "CONFIG", {"subject": "unit", "source_revision": "a", "suite_revision": "b", "tools": {"python": "3.12.3"}, "operator_set": "unit", "unverified_scope": "none"})
            append_record(log, "BASELINE", {"tests": {"tests": 1, "passed": 1, "failures": 0, "errors": 0, "skipped": 0}, "coverage": {"covered": 1, "statements": 1, "percent": 100.0}, "runtime_seconds": 0.01, "deterministic": True})
            append_record(log, "MUTANT_RESULT", {"id": "1", "location": "x.py:1", "operator": "unit", "outcome": "KILLED", "killing_test": "test_x"})
            append_record(log, "MUTANT_RESULT", {"id": "2", "location": "x.py:2", "operator": "unit", "outcome": "SURVIVED", "killing_test": None})
            append_record(log, "TRIAGE", {"mutant_id": "2", "classification": "EQUIVALENT"})
            payload = certificate_payload_from_records(load_records(log), {"type": "CERTIFICATE", "payload": {"config_hash": config["hash"]}})
            append_record(log, "CERTIFICATE", payload)
            data = bytearray(log.read_bytes())
            index = data.find(b'"unit"')
            self.assertNotEqual(index, -1)
            data[index + 1] ^= 0x01
            log.write_bytes(bytes(data))
            result = subprocess.run([sys.executable, str(REPO / "verify.py"), str(log)], capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertRegex(result.stdout, r"^seq 1\b")


if __name__ == "__main__":
    unittest.main()
