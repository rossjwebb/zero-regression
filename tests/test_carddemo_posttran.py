# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "carddemo"
EVIDENCE = SUBJECT / "evidence"


class CardDemoPosttranTests(unittest.TestCase):
    def test_job_runner_is_fail_closed_and_honest(self) -> None:
        script_path = SUBJECT / "run-posttran.sh"
        script = script_path.read_text(encoding="utf-8")
        self.assertTrue(script_path.stat().st_mode & 0o111)
        self.assertIn("S3 FAIL-CLOSED", script)
        self.assertIn("S3 POSTTRAN OK", script)
        self.assertIn("runtime=gnucobol-indexed-bdb-fixture", script)
        self.assertIn("ibm_vsam=false", script)
        self.assertIn("not IBM VSAM", script)
        self.assertIn("paper_s3=unexecuted", script)
        self.assertIn("seed-indexed.cbl", script)
        self.assertIn("cee3abd.cbl", script)
        self.assertIn("run-cobol.sh", script)
        self.assertNotIn("killed/seeded", script)
        self.assertFalse((SUBJECT / "legacy").exists())
        self.assertFalse((SUBJECT / "golden").exists())

    def test_job_receipt_is_score_free(self) -> None:
        receipt = json.loads((EVIDENCE / "job-receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["mutation_score"], "not-stored")
        self.assertEqual(receipt["paper_s3"], "unexecuted")
        self.assertEqual(receipt["posttran_job"], "run")
        self.assertEqual(receipt["runtime"], "gnucobol-indexed-bdb-fixture")
        self.assertIs(receipt["ibm_vsam"], False)
        self.assertIs(receipt["ibm_cics"], False)
        self.assertEqual(receipt["ibm_le_cee3abd"], "stub")
        self.assertEqual(receipt["program_return_code"], 4)
        self.assertEqual(receipt["transactions_processed"], 2)
        self.assertEqual(receipt["transactions_rejected"], 1)
        self.assertIs(receipt["records_mutation_score"], False)
        self.assertIs(receipt["work_receipt_body_stored"], False)
        self.assertNotIsInstance(receipt["mutation_score"], (int, float))

    def test_check_posttran_committed_pack(self) -> None:
        completed = subprocess.run(
            ["python3.12", str(SUBJECT / "check-posttran.py")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("S3 POSTTRAN EVIDENCE OK", completed.stdout)
        self.assertIn("posttran_job=run", completed.stdout)
        self.assertIn("mutation_score=not-stored", completed.stdout)
        self.assertNotIn("killed/seeded", completed.stdout.lower())

    def test_runner_executes_job_when_cobc_is_present(self) -> None:
        completed = subprocess.run(
            [str(SUBJECT / "run-posttran.sh")],
            check=False,
            capture_output=True,
            text=True,
        )
        combined = completed.stdout + completed.stderr
        self.assertNotIn("killed/seeded", combined.lower())
        if not shutil.which("cobc"):
            self.assertEqual(completed.returncode, 2, combined)
            self.assertIn("S3 FAIL-CLOSED", combined)
            return
        self.assertEqual(completed.returncode, 0, combined)
        self.assertIn("S3 POSTTRAN OK", combined)
        self.assertIn("posttran_job=run", combined)
        self.assertIn("runtime=gnucobol-indexed-bdb-fixture", combined)
        self.assertIn("TRANSACTIONS PROCESSED :000000002", combined)
        self.assertIn("TRANSACTIONS REJECTED  :000000001", combined)
        self.assertIn("not IBM VSAM", combined)
        receipt = (SUBJECT / "work" / "POSTTRAN").read_text(encoding="utf-8")
        self.assertIn("posttran_job=run", receipt)
        self.assertIn("program_return_code=4", receipt)
        self.assertIn("ibm_vsam=false", receipt)
        self.assertIn("paper_s3=unexecuted", receipt)
        live = subprocess.run(
            ["python3.12", str(SUBJECT / "check-posttran.py"), "--require-live"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(live.returncode, 0, live.stderr)
        self.assertIn("require-live", live.stdout)
