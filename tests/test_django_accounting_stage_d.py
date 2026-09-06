# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "django-accounting"
ORACLE = SUBJECT / "oracle.py"
DISCRIMINATION = SUBJECT / "check-discrimination.py"
GATE = SUBJECT / "check-stage-d.py"
EVALUATE = SUBJECT / "evidence" / "stage-d" / "evaluate-candidate.py"
STAGE_D = SUBJECT / "evidence" / "stage-d"
POSTURE = STAGE_D / "posture.json"
ENGLISH = STAGE_D / "EVIDENCE.md"
ORACLE_CLAIM = SUBJECT / "ORACLE.md"
PROGRAMME = REPO / "PROGRAMME.md"
README = REPO / "README.md"
SUBJECT_README = SUBJECT / "README.md"
PARENT_EVIDENCE = SUBJECT / "evidence" / "EVIDENCE.md"
STAGE_B_CURSOR = SUBJECT / "evidence" / "arms" / "cursor" / "arm.json"
LEGACY_PRICES = SUBJECT / "legacy" / "accounting" / "libs" / "prices.py"
ORACLE_WORKFLOW = REPO / ".github" / "workflows" / "s1-django-accounting-oracle.yml"
STAGE_D_WORKFLOW = REPO / ".github" / "workflows" / "s1-django-accounting-stage-d.yml"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_OK = f"ORACLE OK pin={PIN} cases=27 replay-only"
CANDIDATES = ("price-faithful", "price-tax-ignored", "profits-no-window")
WEAK = ("price-tax-ignored", "profits-no-window")


class DjangoAccountingStageDTests(unittest.TestCase):
    def test_good_pin_still_prints_the_replay_ok_line(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ORACLE)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED_OK + "\n")

    def test_discrimination_is_still_green(self) -> None:
        result = subprocess.run(
            [sys.executable, str(DISCRIMINATION)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DISCRIMINATION OK", result.stdout)
        self.assertIn("known_bad_rejected=5", result.stdout)
        self.assertIn("golden_echo_rejected=1", result.stdout)
        self.assertIn("clamp_to_zero_rejected=1", result.stdout)

    def test_each_candidate_is_evaluated(self) -> None:
        for name in CANDIDATES:
            with self.subTest(candidate=name):
                result = subprocess.run(
                    [sys.executable, str(EVALUATE), "--candidate", name],
                    cwd=REPO,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                receipt = json.loads(result.stdout)
                self.assertIs(receipt["produced"], True)
                self.assertIn(receipt["gate"]["verdict"], ("accepted", "rejected"))
                self.assertEqual(receipt["paper_s1"], "unexecuted")
                self.assertEqual(receipt["mutation_score"], "not-stored")
                self.assertEqual(receipt["pin"], PIN)
                self.assertFalse(receipt["legacy_edited"])
                self.assertFalse(receipt["golden_widened"])
                stored = json.loads(
                    (STAGE_D / "arms" / "cursor" / "receipts" / f"{name}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(stored["gate"]["verdict"], receipt["gate"]["verdict"])
                self.assertEqual(
                    stored["oracle"]["mismatched_cases"],
                    receipt["oracle"]["mismatched_cases"],
                )

    def test_intentional_weak_candidates_are_rejected(self) -> None:
        for name in WEAK:
            with self.subTest(candidate=name):
                result = subprocess.run(
                    [sys.executable, str(EVALUATE), "--candidate", name],
                    cwd=REPO,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                receipt = json.loads(result.stdout)
                self.assertEqual(receipt["gate"]["verdict"], "rejected", receipt)
                self.assertNotEqual(receipt["oracle"]["exit"], 0)
                self.assertGreater(receipt["oracle"]["mismatch_count"], 0)
                self.assertTrue(receipt["oracle"]["mismatched_cases"])

        tax = json.loads(
            subprocess.run(
                [sys.executable, str(EVALUATE), "--candidate", "price-tax-ignored"],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
            ).stdout
        )
        self.assertIn("price_from_tax", tax["oracle"]["mismatched_cases"])
        self.assertTrue(tax["invariants"]["failed"])

        profits = json.loads(
            subprocess.run(
                [sys.executable, str(EVALUATE), "--candidate", "profits-no-window"],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
            ).stdout
        )
        self.assertIn("profits_period_2024_jan_feb", profits["oracle"]["mismatched_cases"])

    def test_gemini_weak_profits_receipt_stays_historical(self) -> None:
        stored = json.loads(
            (STAGE_D / "arms" / "gemini" / "receipts" / "weak-profits-zero-override.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(stored["gate"]["verdict"], "accepted")
        self.assertFalse(stored["invariants"]["failed"])
        self.assertEqual(stored["oracle"]["match_count"], 27)
        self.assertEqual(stored["oracle"]["mismatch_count"], 0)

        live = json.loads(
            subprocess.run(
                [
                    sys.executable,
                    str(EVALUATE),
                    "--arm",
                    "gemini",
                    "--candidate",
                    "weak-profits-zero-override",
                ],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
            ).stdout
        )
        self.assertEqual(live["oracle"]["match_count"], 27)
        self.assertEqual(live["oracle"]["mismatch_count"], 0)
        self.assertTrue(live["invariants"]["failed"], live)
        self.assertIn("cannot go negative", " ".join(live["invariants"]["failures"]))
        self.assertFalse(live["golden_widened"])

    def test_claude_candidates_are_live_evaluated(self) -> None:
        names = (
            "faithful-price-rewrite",
            "weak-price-tax-floor",
            "weak-profits-clamp-nonneg",
        )
        for name in names:
            with self.subTest(candidate=name):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(EVALUATE),
                        "--arm",
                        "claude-code",
                        "--candidate",
                        name,
                    ],
                    cwd=REPO,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                receipt = json.loads(result.stdout)
                self.assertEqual(receipt["arm"], "claude-code")
                self.assertIs(receipt["produced"], True)
                self.assertIn(receipt["gate"]["verdict"], ("accepted", "rejected"))
                self.assertEqual(receipt["paper_s1"], "unexecuted")
                self.assertEqual(receipt["mutation_score"], "not-stored")
                self.assertFalse(receipt["legacy_edited"])
                self.assertFalse(receipt["golden_widened"])
                stored = json.loads(
                    (STAGE_D / "arms" / "claude-code" / "receipts" / f"{name}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(stored["gate"]["verdict"], receipt["gate"]["verdict"])
                self.assertEqual(
                    stored["oracle"]["mismatched_cases"],
                    receipt["oracle"]["mismatched_cases"],
                )
                self.assertEqual(
                    stored["invariants"]["failed"],
                    receipt["invariants"]["failed"],
                )

    def test_claude_weak_profits_is_live_rejected(self) -> None:
        stored = json.loads(
            (
                STAGE_D / "arms" / "claude-code" / "receipts" / "weak-profits-clamp-nonneg.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(stored["gate"]["verdict"], "rejected")
        self.assertTrue(stored["invariants"]["failed"])
        self.assertEqual(stored["oracle"]["match_count"], 27)
        self.assertEqual(stored["oracle"]["mismatch_count"], 0)

        live = json.loads(
            subprocess.run(
                [
                    sys.executable,
                    str(EVALUATE),
                    "--arm",
                    "claude-code",
                    "--candidate",
                    "weak-profits-clamp-nonneg",
                ],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
            ).stdout
        )
        self.assertEqual(live["gate"]["verdict"], "rejected")
        self.assertTrue(live["invariants"]["failed"], live)
        self.assertIn("cannot go negative", " ".join(live["invariants"]["failures"]))
        self.assertFalse(live["golden_widened"])

    def test_stage_d_gate_is_green_and_score_free(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GATE)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith(EXPECTED_OK + "\n"), result.stdout)
        self.assertIn("STAGE D OK", result.stdout)
        self.assertIn("cursor=executed", result.stdout)
        self.assertIn("produced=true", result.stdout)
        self.assertIn("rejected=2", result.stdout)
        self.assertIn("paper_s1=unexecuted", result.stdout)
        self.assertIn("mutation_score=not-stored", result.stdout)
        self.assertIn("discrimination_gate=required", result.stdout)
        self.assertIn("claude_code=executed", result.stdout)
        self.assertIn("claude_code_rejected=1", result.stdout)
        self.assertIn("gemini=executed", result.stdout)
        self.assertIn("gemini_rejected=1", result.stdout)
        self.assertNotIn("killed/seeded", result.stdout.lower())
        self.assertNotIn("kill rate", result.stdout.lower())

    def test_legacy_price_source_is_unpatched(self) -> None:
        text = LEGACY_PRICES.read_text(encoding="utf-8")
        self.assertIn("return self.incl_tax - self.excl_tax", text)
        self.assertNotIn("Decimal(\"0\")", text)

    def test_stage_b_cursor_receipt_stays_historical(self) -> None:
        payload = json.loads(STAGE_B_CURSOR.read_text(encoding="utf-8"))
        self.assertIs(payload["candidate_artefacts"]["produced"], False)
        self.assertEqual(payload["oracle"]["match_count"], 27)
        self.assertEqual(payload["oracle"]["mismatch_count"], 0)

    def test_posture_and_english_are_honest(self) -> None:
        payload = json.loads(POSTURE.read_text(encoding="utf-8"))
        self.assertEqual(payload["stage"], "D")
        self.assertEqual(payload["paper_s1"], "unexecuted")
        self.assertEqual(payload["mutation_score"], "not-stored")
        self.assertEqual(payload["discrimination_gate"], "required")
        self.assertIs(payload["produced"], True)
        self.assertIs(payload["golden_widened"], False)
        self.assertIs(payload["legacy_edited"], False)
        self.assertIs(payload["orm_sql_executed"], False)
        self.assertEqual(payload["codex_arm"], "omitted")
        self.assertEqual(payload["cases"], 27)
        self.assertNotIsInstance(payload["mutation_score"], (int, float))
        self.assertNotIn("kill_rate", payload)
        self.assertEqual(payload["arms"]["cursor"]["status"], "executed")
        self.assertEqual(payload["arms"]["claude_code"]["status"], "executed")
        self.assertEqual(payload["arms"]["gemini"]["status"], "executed")
        english = ENGLISH.read_text(encoding="utf-8")
        self.assertIn("paper_s1=unexecuted", english)
        self.assertIn("mutation_score=not-stored", english)
        self.assertIn("discrimination_gate=required", english)
        self.assertIn("not paper S1", english)
        self.assertIn("rewrite attempt", english)
        self.assertNotIn("generators succeeded", english.lower())
        self.assertNotIn("paper s1 ran", english.lower())
        self.assertIn("historical receipt", english.lower())
        self.assertIn("expenses>collected", english)

    def test_external_slots_do_not_invent_oracle_results(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("s1_stage_d_gate", GATE)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fake = {
            "status": "awaiting-external-run",
            "generators_run": False,
            "paper_s1": "unexecuted",
            "mutation_score": "not-stored",
            "candidate_artefacts": {"produced": False},
            "oracle": {"stdout": EXPECTED_OK, "match_count": 27, "mismatch_count": 0, "exit": 0},
        }
        errors = module.check_awaiting_external_slot("claude-code", fake)
        self.assertTrue(any("invented" in error for error in errors), errors)

    def test_docs_name_stage_d_without_paper_s1(self) -> None:
        for path in (ORACLE_CLAIM, PROGRAMME, README, SUBJECT_README, PARENT_EVIDENCE):
            text = path.read_text(encoding="utf-8")
            self.assertIn("Stage D", text, path)
            self.assertIn("not paper s1", text.lower(), path)
        claim = ORACLE_CLAIM.read_text(encoding="utf-8")
        self.assertIn("rewrite", claim.lower())
        self.assertIn(PIN, claim)

    def test_ci_runs_stage_d_and_does_not_skip_discrimination(self) -> None:
        oracle_workflow = ORACLE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3.12 subjects/django-accounting/oracle.py", oracle_workflow)
        self.assertIn("python3.12 subjects/django-accounting/check-discrimination.py", oracle_workflow)
        self.assertIn("python3.12 subjects/django-accounting/check-stage-d.py", oracle_workflow)
        self.assertNotIn("cases=19", oracle_workflow)
        self.assertTrue(STAGE_D_WORKFLOW.is_file())
        stage_d = STAGE_D_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3.12 subjects/django-accounting/check-discrimination.py", stage_d)
        self.assertIn("python3.12 subjects/django-accounting/check-stage-d.py", stage_d)
        self.assertIn("tests.test_django_accounting_stage_d", stage_d)
        self.assertIn(EXPECTED_OK, stage_d)


if __name__ == "__main__":
    unittest.main()
