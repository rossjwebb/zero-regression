# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import subprocess
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "commons-csv"


class CommonsCsvPinTests(unittest.TestCase):
    def test_check_pins_exits_zero(self) -> None:
        completed = subprocess.run(
            ["python3.12", str(SUBJECT / "check-pins.py")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("S2 PIN OK", completed.stdout)
        self.assertNotIn("mutation score", completed.stdout.lower())

    def test_pins_name_defects4j_csv_and_pit(self) -> None:
        pins = tomllib.loads((SUBJECT / "pins.toml").read_text(encoding="utf-8"))
        self.assertEqual(pins["defects4j"]["tag"], "v3.0.1")
        self.assertEqual(pins["defects4j"]["commit"], "6d54320e0db5a357f9ab38a8e4d2e5aead7e1c09")
        self.assertEqual(pins["defects4j"]["project"], "Csv")
        self.assertEqual(pins["defects4j"]["project_name"], "commons-csv")
        self.assertEqual(pins["defects4j"]["version"], "1f")
        self.assertEqual(pins["commons_csv"]["commit"], "de1838ea067f3fbc4c7c21b9eeae077c739ecb73")
        self.assertEqual(pins["pit"]["tool"], "pitest")
        self.assertEqual(pins["pit"]["version"], "1.15.3")
        self.assertEqual(pins["pit"]["target_class"], "org.apache.commons.csv.ExtendedBufferedReader")

    def test_run_script_is_fail_closed_and_does_not_record_a_score(self) -> None:
        script = (SUBJECT / "run-pit.sh").read_text(encoding="utf-8")
        self.assertTrue((SUBJECT / "run-pit.sh").stat().st_mode & 0o111)
        self.assertIn("S2 FAIL-CLOSED", script)
        self.assertIn("does not record a mutation score", script)
        self.assertIn("pitest.mutationtest.commandline.MutationCoverageReport", script)
        self.assertNotIn("defects4j mutation", script)

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
