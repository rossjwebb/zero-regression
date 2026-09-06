# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "commons-csv"
if str(SUBJECT) not in sys.path:
    sys.path.insert(0, str(SUBJECT))

from toolchain import (  # noqa: E402
    build_live_receipt,
    classify_live_work,
    contains_forbidden_score_text,
    load_pins,
    receipt_score_errors,
)

EVIDENCE = SUBJECT / "evidence"
POSTURE = EVIDENCE / "s2-posture.json"
RECEIPT = EVIDENCE / "pit-receipt.json"
ENGLISH = EVIDENCE / "EVIDENCE.md"
GATE = SUBJECT / "check-s2-pit.py"
RECORDER = SUBJECT / "record-pit-receipt.py"
PROGRAMME = REPO / "PROGRAMME.md"
README = REPO / "README.md"
SUBJECT_README = SUBJECT / "README.md"
WORKFLOW = REPO / ".github" / "workflows" / "s2-commons-csv.yml"
EXPECTED_OK = (
    "S2 PIT EVIDENCE OK "
    "mutation_score=not-stored "
    "paper_s2=unexecuted"
)
CLEAN_LOG = (
    "> org.pitest.mutationtest.engine.gregor.mutators.MathMutator\n"
    "> KILLED 1 SURVIVED 0 TIMED_OUT 0 NON_VIABLE 0\n"
    "> MEMORY_ERROR 0 NOT_STARTED 0 STARTED 0 RUN_ERROR 0\n"
)
TIMEOUT_LOG = (
    "PIT >> WARNING : Minion exited abnormally due to TIMED_OUT\n"
    "> KILLED 3 SURVIVED 0 TIMED_OUT 1 NON_VIABLE 0\n"
    "> MEMORY_ERROR 0 NOT_STARTED 0 STARTED 0 RUN_ERROR 0\n"
    ">> Generated 34 mutations Killed 12 (35%)\n"
)


def _write_work(root: Path, *, log: str | None, html: bool) -> Path:
    work = root / "work"
    (work / "pit-reports").mkdir(parents=True)
    if log is not None:
        (work / "pit.log").write_text(log, encoding="utf-8")
    if html:
        (work / "pit-reports" / "index.html").write_text("<html>redacted</html>\n", encoding="utf-8")
    return work


class CommonsCsvPitEvidenceTests(unittest.TestCase):
    def test_missing_work_is_blocked_pit_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "work"
            work.mkdir()
            executed, blocked, errors = classify_live_work(work)
            self.assertFalse(executed)
            self.assertEqual(blocked, "pit-not-run")
            self.assertEqual(errors, [])

    def test_clean_work_classifies_as_executed_without_a_score(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = _write_work(Path(temporary), log=CLEAN_LOG, html=True)
            executed, blocked, errors = classify_live_work(work, pit_rc=0)
            self.assertTrue(executed)
            self.assertIsNone(blocked)
            self.assertEqual(errors, [])
            receipt = build_live_receipt(
                pins=load_pins(),
                work=work,
                python_version="3.12.3",
                pit_rc=0,
            )
            self.assertEqual(receipt["mutation_score"], "not-stored")
            self.assertEqual(receipt["paper_s2"], "unexecuted")
            self.assertEqual(receipt["status"], "live-pit-executed")
            self.assertIs(receipt["executed"], True)
            self.assertIsNone(receipt["blocked"])
            self.assertIs(receipt["html_report_present"], True)
            self.assertIs(receipt["html_report_body_stored"], False)
            self.assertIs(receipt["pit_log_body_stored"], False)
            self.assertIs(receipt["records_mutation_score"], False)
            self.assertNotIn("killed", receipt)
            self.assertNotIn("kill_rate", receipt)
            self.assertEqual(receipt_score_errors(receipt), [])
            dumped = json.dumps(receipt)
            self.assertFalse(contains_forbidden_score_text(dumped))
            self.assertNotIn("35%", dumped)
            self.assertNotIn("killed/seeded", dumped)

    def test_timed_out_work_is_blocked_and_stores_no_score(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = _write_work(Path(temporary), log=TIMEOUT_LOG, html=True)
            executed, blocked, errors = classify_live_work(work, pit_rc=0)
            self.assertFalse(executed)
            self.assertEqual(blocked, "pit-judge-fail-closed")
            self.assertTrue(any("TIMED_OUT" in item for item in errors))
            receipt = build_live_receipt(
                pins=load_pins(),
                work=work,
                python_version="3.12.3",
                pit_rc=0,
            )
            self.assertEqual(receipt["status"], "blocked=pit-judge-fail-closed")
            self.assertIs(receipt["executed"], False)
            self.assertEqual(receipt["mutation_score"], "not-stored")
            self.assertNotIn("35%", json.dumps(receipt))
            self.assertEqual(receipt_score_errors(receipt), [])

    def test_numeric_mutation_score_is_rejected(self) -> None:
        errors = receipt_score_errors({"mutation_score": 91.0, "killed": 12})
        self.assertTrue(any("must not be numeric" in item for item in errors))

    def test_score_text_detector_allows_not_stored(self) -> None:
        self.assertFalse(contains_forbidden_score_text("mutation_score=not-stored"))
        self.assertTrue(contains_forbidden_score_text("mutation_score=91.0"))
        self.assertTrue(contains_forbidden_score_text("Generated 34 mutations Killed 12 (35%)"))
        self.assertTrue(contains_forbidden_score_text("killed/seeded 12/34"))

    def test_committed_pack_is_score_free_and_live_or_blocked(self) -> None:
        self.assertTrue(POSTURE.is_file())
        self.assertTrue(RECEIPT.is_file())
        self.assertTrue(ENGLISH.is_file())
        posture = json.loads(POSTURE.read_text(encoding="utf-8"))
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(posture["mutation_score"], "not-stored")
        self.assertEqual(posture["paper_s2"], "unexecuted")
        self.assertEqual(receipt["mutation_score"], "not-stored")
        self.assertEqual(receipt["paper_s2"], "unexecuted")
        self.assertNotIsInstance(posture["mutation_score"], (int, float))
        self.assertIsInstance(posture["mutation_score"], str)
        status = posture["status"]
        self.assertTrue(
            status == "live-pit-executed" or str(status).startswith("blocked="),
            status,
        )
        self.assertEqual(status, receipt["status"])
        if status == "live-pit-executed":
            self.assertIs(receipt["executed"], True)
            self.assertIsNone(receipt["blocked"])
            self.assertIs(posture["runner"]["executed_in_this_pack"], True)
        else:
            self.assertIs(receipt["executed"], False)
            self.assertEqual(receipt["blocked"], status.split("=", 1)[1])
        self.assertIs(receipt["records_mutation_score"], False)
        self.assertIs(receipt["html_report_body_stored"], False)
        self.assertIs(receipt["pit_log_body_stored"], False)
        self.assertFalse(receipt.get("html_report_tracked"))
        self.assertEqual(receipt_score_errors(posture), [])
        self.assertEqual(receipt_score_errors(receipt), [])
        english = ENGLISH.read_text(encoding="utf-8")
        self.assertIn("mutation_score=not-stored", english)
        self.assertIn("paper_s2=unexecuted", english)
        self.assertIn(f"status={status}", english)
        self.assertIn("not a paper execution of S2", english)
        self.assertFalse(contains_forbidden_score_text(english))

    def test_gate_is_green_and_score_free(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GATE)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("S2 PIN OK", result.stdout)
        self.assertIn(EXPECTED_OK, result.stdout)
        self.assertIn("mutation_score=not-stored", result.stdout)
        self.assertIn("paper_s2=unexecuted", result.stdout)
        self.assertNotIn("killed/seeded", result.stdout.lower())
        self.assertNotIn("kill rate", result.stdout.lower())
        self.assertNotRegex(result.stdout, r"\b\d+(\.\d+)?%")

    def test_recorder_refuses_to_store_html_body(self) -> None:
        script = RECORDER.read_text(encoding="utf-8")
        self.assertIn("html_report_body_stored", script)
        self.assertIn("score-free", script)
        self.assertIn("Never copies pit.log", script)

    def test_docs_name_live_pit_without_paper_s2(self) -> None:
        for path in (PROGRAMME, README, SUBJECT_README, ENGLISH):
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("mutation_score=not-stored", text.replace("`", ""), path)
            self.assertIn("not paper s2", text, path)

    def test_ci_runs_live_pit_and_does_not_skip(self) -> None:
        self.assertTrue(WORKFLOW.is_file())
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3.12 subjects/commons-csv/check-pins.py", workflow)
        self.assertIn("./subjects/commons-csv/run-pit.sh", workflow)
        self.assertIn("python3.12 subjects/commons-csv/check-s2-pit.py --require-live", workflow)
        self.assertIn("Skip is not a pass", workflow)
        self.assertNotIn("mode=skip", workflow)
        self.assertNotIn("java-version: \"21\"", workflow)
        self.assertIn("tests.test_commons_csv_pit_evidence", workflow)


if __name__ == "__main__":
    unittest.main()
