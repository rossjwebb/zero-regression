# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import subprocess
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "commons-csv"
EVIDENCE = SUBJECT / "evidence"
POSTURE = EVIDENCE / "s2-posture.json"


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
        self.assertEqual(pins["pit"]["mutators"], "DEFAULTS")
        self.assertEqual(pins["pit"]["subject_release"], 8)
        self.assertEqual(pins["pit"]["target_class"], "org.apache.commons.csv.ExtendedBufferedReader")
        self.assertEqual(pins["jdk"]["release"], "11.0.32.1+1")
        self.assertTrue(pins["jdk"]["sha256"])
        self.assertIn("org.apache.commons.csv.CSVParser", pins["pit"]["excluded_classes"])

    def test_run_script_is_fail_closed_and_does_not_record_a_score(self) -> None:
        script = (SUBJECT / "run-pit.sh").read_text(encoding="utf-8")
        self.assertTrue((SUBJECT / "run-pit.sh").stat().st_mode & 0o111)
        self.assertIn("S2 FAIL-CLOSED", script)
        self.assertIn("does not record a mutation score", script)
        self.assertIn("pitest.mutationtest.commandline.MutationCoverageReport", script)
        self.assertIn("--mutators", script)
        self.assertIn("judge_pit_log", script)
        self.assertIn("S2_JAVA_HOME", script)
        self.assertNotIn("defects4j mutation", script)
        self.assertNotIn("java-version: \"21\"", script)

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
        self.assertEqual(payload["paper_s2"], "unexecuted")
        self.assertEqual(payload["status"], "scaffolding+runner-only")
        self.assertNotIsInstance(payload["mutation_score"], (int, float))
        self.assertIsInstance(payload["mutation_score"], str)
        claims = payload["claims"]
        self.assertEqual(claims["mutation_score"], "not-stored")
        self.assertEqual(claims["paper_s2"], "unexecuted")
        self.assertEqual(claims["status"], "scaffolding+runner-only")
        self.assertNotIsInstance(claims["mutation_score"], (int, float))
        self._assert_no_numeric_mutation_score(payload)
        english = (EVIDENCE / "EVIDENCE.md").read_text(encoding="utf-8")
        self.assertIn("mutation_score=not-stored", english)
        self.assertIn("paper_s2=unexecuted", english)
        self.assertIn("status=scaffolding+runner-only", english)
        self.assertIn("not a paper execution of s2", english.lower())

    def test_evidence_records_pins_gate_and_fail_closed_runner(self) -> None:
        pins = tomllib.loads((SUBJECT / "pins.toml").read_text(encoding="utf-8"))
        payload = json.loads(POSTURE.read_text(encoding="utf-8"))
        recorded = payload["pins"]
        self.assertEqual(recorded["defects4j"]["commit"], pins["defects4j"]["commit"])
        self.assertEqual(recorded["defects4j"]["tag"], pins["defects4j"]["tag"])
        self.assertEqual(recorded["commons_csv"]["commit"], pins["commons_csv"]["commit"])
        self.assertEqual(recorded["pit"]["tool"], pins["pit"]["tool"])
        self.assertEqual(recorded["pit"]["version"], pins["pit"]["version"])
        self.assertEqual(recorded["pit"]["mutators"], pins["pit"]["mutators"])
        self.assertEqual(recorded["jdk"]["release"], pins["jdk"]["release"])
        self.assertEqual(recorded["jdk"]["sha256"], pins["jdk"]["sha256"])
        self.assertEqual(payload["pin_gate"]["path"], "subjects/commons-csv/check-pins.py")
        self.assertEqual(payload["pin_gate"]["role"], "gate")
        self.assertEqual(payload["pin_gate"]["exit"], 0)
        self.assertEqual(payload["pin_gate"]["python"], "3.12.3")
        self.assertTrue(payload["pin_gate"]["stdout"].startswith("S2 PIN OK"))
        self.assertEqual(payload["runner"]["path"], "subjects/commons-csv/run-pit.sh")
        self.assertTrue(payload["runner"]["fail_closed"])
        self.assertFalse(payload["runner"]["records_mutation_score"])
        self.assertFalse(payload["runner"]["executed_in_this_pack"])
        self.assertEqual(
            payload["runner"]["exits_nonzero_on"],
            ["TIMED_OUT", "MEMORY_ERROR", "RUN_ERROR"],
        )
        script = (SUBJECT / "run-pit.sh").read_text(encoding="utf-8")
        self.assertIn("judge_pit_log", script)
        self.assertIn("S2 FAIL-CLOSED", script)

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
