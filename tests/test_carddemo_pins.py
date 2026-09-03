# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import shutil
import subprocess
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "carddemo"


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
        self.assertIn("no score is recorded", script)
        self.assertIn("toolchain.py", script)
        self.assertIn("S3_COBC", script)
        self.assertIn("-x", script)
        self.assertNotIn("killed/seeded", script)

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
            self.assertIn("compiled cbtrn02c", combined)
            self.assertIn("no legacy tests", combined)
            self.assertIn("not a green posttran job", combined)
            self.assertTrue((SUBJECT / "work" / "CBTRN02C").is_file())
            self.assertTrue((SUBJECT / "work" / "COMPILE").is_file())
            receipt = (SUBJECT / "work" / "COMPILE").read_text(encoding="utf-8")
            self.assertIn("result=compile-ok", receipt)
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
