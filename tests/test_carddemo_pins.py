# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "carddemo"
EVIDENCE = SUBJECT / "evidence"
POSTURE = EVIDENCE / "s3-posture.json"


class CardDemoPinTests(unittest.TestCase):
    def test_check_pins_exits_zero(self) -> None:
        completed = subprocess.run(
            ["python3.12", str(SUBJECT / "check-pins.py")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("S3 PIN OK", completed.stdout)
        self.assertNotIn("mutation score", completed.stdout.lower())

    def test_pins_name_public_carddemo_and_no_legacy_tests(self) -> None:
        pins = tomllib.loads((SUBJECT / "pins.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            pins["carddemo"]["upstream"],
            "https://github.com/aws-samples/aws-mainframe-modernization-carddemo",
        )
        self.assertEqual(pins["carddemo"]["commit"], "59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e")
        self.assertEqual(pins["carddemo"]["legacy_tests"], "none")
        self.assertEqual(pins["carddemo"]["licence"], "Apache-2.0")
        self.assertEqual(pins["slice"]["job"], "POSTTRAN")
        self.assertEqual(pins["slice"]["program"], "CBTRN02C")
        self.assertEqual(pins["carddemo"]["file_count"], 329)

    def test_no_legacy_or_golden_tree(self) -> None:
        self.assertFalse((SUBJECT / "legacy").exists())
        self.assertFalse((SUBJECT / "golden").exists())
        toml = tomllib.loads((SUBJECT / "zero-regression.toml").read_text(encoding="utf-8"))
        self.assertEqual(toml["subject"]["test_paths"], [])

    def test_run_script_is_fail_closed_and_does_not_record_a_score(self) -> None:
        script_path = SUBJECT / "run-cobol.sh"
        script = script_path.read_text(encoding="utf-8")
        self.assertTrue(script_path.stat().st_mode & 0o111)
        self.assertIn("S3 FAIL-CLOSED", script)
        self.assertIn("S3 COBC FAIL", script)
        self.assertIn("S3 HARNESS EXIT 2", script)
        self.assertIn("no score is recorded", script)
        self.assertIn("toolchain.py", script)
        self.assertIn("S3_COBC", script)
        self.assertIn("-x", script)
        self.assertNotIn("killed/seeded", script)
        # Compile-OK must stay at harness exit 2, not look like a passing job.
        self.assertIn("Do not change compile-OK to exit 0", script)

    def test_runner_exits_nonzero_with_a_real_reason(self) -> None:
        completed = subprocess.run(
            [str(SUBJECT / "run-cobol.sh")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2, completed.stderr + completed.stdout)
        self.assertIn("S3 FAIL-CLOSED", completed.stderr)
        combined = (completed.stderr + completed.stdout).lower()
        self.assertNotIn("killed/seeded", combined)
        self.assertIn("no score is recorded", combined)
        self.assertNotRegex(combined, r"killed/\s*seeded")
        # If the pinned cobc is present the script must compile CBTRN02C
        # and still fail closed (no legacy tests, not a POSTTRAN job).
        # If cobc is missing or the pin mismatches it must say so.
        if shutil.which("cobc"):
            self.assertIn("s3 compile ok", combined)
            self.assertIn("s3 harness exit 2", combined)
            self.assertIn("not a gnucobol error", combined)
            self.assertIn("compiled cbtrn02c", combined)
            self.assertIn("no legacy tests", combined)
            self.assertIn("not a green posttran job", combined)
            self.assertNotIn("s3 cobc fail", combined)
            self.assertFalse((SUBJECT / "work" / "COBC-FAIL").exists())
            self.assertTrue((SUBJECT / "work" / "CBTRN02C").is_file())
            self.assertTrue((SUBJECT / "work" / "COMPILE").is_file())
            receipt = (SUBJECT / "work" / "COMPILE").read_text(encoding="utf-8")
            self.assertIn("result=compile-ok", receipt)
            self.assertIn("cobc_status=0", receipt)
            self.assertIn("harness_exit=2", receipt)
            self.assertIn("harness_meaning=posttran-job-not-run", receipt)
            self.assertIn("mutation_score=not-recorded", receipt)
            self.assertIn("posttran_job=not-run", receipt)
            self.assertIn("compiler_release=3.1.2.0", receipt)
        else:
            self.assertTrue(
                "pinned cobc is missing" in combined or "missing" in combined,
                completed.stderr,
            )

    def test_no_committed_mutation_score(self) -> None:
        forbidden_names = {"mutations.xml", "SCORE", "mutation-score"}
        tracked = [
            path
            for path in SUBJECT.rglob("*")
            if path.is_file() and "work" not in path.parts
        ]
        names = {path.name for path in tracked}
        self.assertTrue(forbidden_names.isdisjoint(names))
        for path in tracked:
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            self.assertNotIn("killed/seeded", text)

    def test_evidence_claim_fields_forbid_numeric_mutation_score(self) -> None:
        self.assertTrue(POSTURE.is_file())
        self.assertTrue((EVIDENCE / "EVIDENCE.md").is_file())
        payload = json.loads(POSTURE.read_text(encoding="utf-8"))
        self.assertEqual(payload["mutation_score"], "not-stored")
        self.assertEqual(payload["paper_s3"], "unexecuted")
        self.assertEqual(payload["status"], "scaffolding+compile-runner-only")
        self.assertEqual(payload["posttran_job"], "not-run")
        self.assertIs(payload["executed_job"], False)
        self.assertNotIsInstance(payload["mutation_score"], (int, float))
        self.assertIsInstance(payload["mutation_score"], str)
        claims = payload["claims"]
        self.assertEqual(claims["mutation_score"], "not-stored")
        self.assertEqual(claims["paper_s3"], "unexecuted")
        self.assertEqual(claims["status"], "scaffolding+compile-runner-only")
        self.assertEqual(claims["posttran_job"], "not-run")
        self.assertIs(claims["executed_job"], False)
        self.assertNotIsInstance(claims["mutation_score"], (int, float))
        self._assert_no_numeric_mutation_score(payload)
        english = (EVIDENCE / "EVIDENCE.md").read_text(encoding="utf-8")
        self.assertIn("mutation_score=not-stored", english)
        self.assertIn("paper_s3=unexecuted", english)
        self.assertIn("status=scaffolding+compile-runner-only", english)
        self.assertIn("posttran_job=not-run", english)
        self.assertIn("executed_job=false", english)
        self.assertIn("not a paper execution of s3", english.lower())
        self.assertIn("compiling is not paper s3", english.lower())

    def test_evidence_records_pins_gate_and_fail_closed_runner(self) -> None:
        pins = tomllib.loads((SUBJECT / "pins.toml").read_text(encoding="utf-8"))
        zr = tomllib.loads((SUBJECT / "zero-regression.toml").read_text(encoding="utf-8"))
        payload = json.loads(POSTURE.read_text(encoding="utf-8"))
        recorded = payload["pins"]
        self.assertEqual(recorded["carddemo"]["commit"], pins["carddemo"]["commit"])
        self.assertEqual(recorded["carddemo"]["upstream"], pins["carddemo"]["upstream"])
        self.assertEqual(recorded["carddemo"]["legacy_tests"], pins["carddemo"]["legacy_tests"])
        self.assertEqual(recorded["slice"]["job"], pins["slice"]["job"])
        self.assertEqual(recorded["slice"]["program"], pins["slice"]["program"])
        self.assertEqual(recorded["slice"]["program_path"], pins["slice"]["program_path"])
        self.assertEqual(recorded["gnucobol"]["package"], pins["gnucobol"]["package"])
        self.assertEqual(recorded["gnucobol"]["version"], pins["gnucobol"]["version"])
        self.assertEqual(recorded["gnucobol"]["release"], pins["gnucobol"]["release"])
        self.assertEqual(recorded["gnucobol"]["url"], pins["gnucobol"]["url"])
        self.assertEqual(recorded["gnucobol"]["sha256"], pins["gnucobol"]["sha256"])
        self.assertEqual(recorded["gnucobol"]["cobc_sha256"], pins["gnucobol"]["cobc_sha256"])
        self.assertEqual(recorded["zero_regression"]["test_paths"], zr["subject"]["test_paths"])
        self.assertEqual(recorded["zero_regression"]["operator_set"], zr["subject"]["operator_set"])
        self.assertEqual(payload["pin_gate"]["path"], "subjects/carddemo/check-pins.py")
        self.assertEqual(payload["pin_gate"]["role"], "gate")
        self.assertEqual(payload["pin_gate"]["exit"], 0)
        self.assertEqual(payload["pin_gate"]["python"], "3.12.3")
        self.assertTrue(payload["pin_gate"]["stdout"].startswith("S3 PIN OK"))
        self.assertIn("pin integrity only", payload["pin_gate"]["meaning"])
        self.assertIn("not a POSTTRAN job result", payload["pin_gate"]["meaning"])
        self.assertEqual(payload["runner"]["path"], "subjects/carddemo/run-cobol.sh")
        self.assertTrue(payload["runner"]["fail_closed"])
        self.assertFalse(payload["runner"]["records_mutation_score"])
        self.assertFalse(payload["runner"]["executed_in_this_pack"])
        self.assertIs(payload["runner"]["executed_job"], False)
        self.assertEqual(payload["runner"]["posttran_job"], "not-run")
        self.assertEqual(payload["runner"]["compile_ok_marker"], "S3 COMPILE OK")
        self.assertEqual(payload["runner"]["harness_exit_2_marker"], "S3 HARNESS EXIT 2")
        self.assertEqual(payload["runner"]["compile_ok_exit"], 2)
        self.assertEqual(payload["runner"]["compile_ok_meaning"], "posttran_job=not-run")
        self.assertEqual(payload["runner"]["cobc_fail_marker"], "S3 COBC FAIL")
        script = (SUBJECT / "run-cobol.sh").read_text(encoding="utf-8")
        self.assertIn("S3 COMPILE OK", script)
        self.assertIn("S3 COBC FAIL", script)
        self.assertIn("S3 HARNESS EXIT 2", script)
        self.assertIn("S3 FAIL-CLOSED", script)
        self.assertIn("Do not change compile-OK to exit 0", script)

    def _assert_no_numeric_mutation_score(self, node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "mutation_score":
                    self.assertFalse(isinstance(value, (int, float)), value)
                    self.assertIn(value, ("not-stored", None))
                self._assert_no_numeric_mutation_score(value)
        elif isinstance(node, list):
            for item in node:
                self._assert_no_numeric_mutation_score(item)
