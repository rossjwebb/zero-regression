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
GATE = SUBJECT / "check-discrimination.py"
RUN_ORACLE = SUBJECT / "discrimination" / "run_oracle.py"
POSTURE = SUBJECT / "evidence" / "discrimination" / "posture.json"
ENGLISH = SUBJECT / "evidence" / "discrimination" / "EVIDENCE.md"
ORACLE_CLAIM = SUBJECT / "ORACLE.md"
LEGACY_PRICES = SUBJECT / "legacy" / "accounting" / "libs" / "prices.py"
LEGACY_CALCULATORS = SUBJECT / "legacy" / "accounting" / "apps" / "books" / "calculators.py"
ORACLE_WORKFLOW = REPO / ".github" / "workflows" / "s1-django-accounting-oracle.yml"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_OK = f"ORACLE OK pin={PIN} cases=27 replay-only"
KNOWN_BAD = (
    ("bad_price_tax_zero", "price_from_tax"),
    ("bad_fully_paid", "invoice_fully_paid"),
    ("bad_profits", "profits_period_2024_jan_feb"),
    ("bad_mixed_rate_silent", "payment_allocation_mixed_rate"),
    ("bad_unknown_tax_silent", "price_unknown_tax_access"),
)


class DjangoAccountingDiscriminationTests(unittest.TestCase):
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

    def test_each_known_bad_probe_fails_a_named_case(self) -> None:
        for name, case in KNOWN_BAD:
            with self.subTest(probe=name):
                result = subprocess.run(
                    [sys.executable, str(RUN_ORACLE), "--probe", name],
                    cwd=REPO,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("ORACLE FAILURE", result.stderr)
                self.assertIn(f"case {case}:", result.stderr)

    def test_golden_echo_can_pass_replay_and_fails_invariants(self) -> None:
        echo = subprocess.run(
            [sys.executable, str(RUN_ORACLE), "--probe", "golden_echo"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(echo.returncode, 0, echo.stderr)
        self.assertEqual(echo.stdout, EXPECTED_OK + "\n")

        if str(SUBJECT / "discrimination") not in sys.path:
            sys.path.insert(0, str(SUBJECT / "discrimination"))
        import invariants

        errors = invariants.check_golden_echo_invariants()
        self.assertTrue(errors)
        self.assertTrue(any("pin not executed" in item for item in errors), errors)
        live = invariants.check_live_invariants()
        self.assertEqual(live, [], live)

    def test_discrimination_gate_is_green_and_fail_closed(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GATE)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith(EXPECTED_OK + "\n"), result.stdout)
        self.assertIn("DISCRIMINATION OK", result.stdout)
        self.assertIn("good_pin=pass", result.stdout)
        self.assertIn("known_bad_rejected=5", result.stdout)
        self.assertIn("golden_echo_rejected=1", result.stdout)
        self.assertIn("invariants=3", result.stdout)
        self.assertIn("paper_s1=unexecuted", result.stdout)
        self.assertIn("mutation_score=not-stored", result.stdout)
        self.assertNotIn("killed/seeded", result.stdout.lower())
        self.assertNotIn("kill rate", result.stdout.lower())

    def test_legacy_price_source_is_unpatched(self) -> None:
        text = LEGACY_PRICES.read_text(encoding="utf-8")
        self.assertIn("return self.incl_tax - self.excl_tax", text)
        self.assertNotIn("Decimal(\"0\")", text)

    def test_legacy_calculators_still_raise_on_mixed_rate(self) -> None:
        text = LEGACY_CALCULATORS.read_text(encoding="utf-8")
        self.assertIn("raise NotImplementedError", text)
        self.assertIn("multiple tax rates", text)

    def test_posture_is_score_free(self) -> None:
        payload = json.loads(POSTURE.read_text(encoding="utf-8"))
        self.assertEqual(payload["paper_s1"], "unexecuted")
        self.assertEqual(payload["mutation_score"], "not-stored")
        self.assertEqual(payload["known_bad_rejected"], 5)
        self.assertEqual(payload["invariants"], 3)
        self.assertIs(payload["golden_echo_rejected"], True)
        self.assertIs(payload["golden_widened"], False)
        self.assertIs(payload["legacy_edited"], False)
        self.assertIs(payload["orm_sql_executed"], False)
        self.assertEqual(payload["cases"], 27)
        self.assertNotIsInstance(payload["mutation_score"], (int, float))
        self.assertNotIn("kill_rate", payload)
        english = ENGLISH.read_text(encoding="utf-8")
        self.assertIn("paper_s1=unexecuted", english)
        self.assertIn("mutation_score=not-stored", english)
        self.assertIn("known_bad_rejected=5", english)
        self.assertIn("not a kill rate", english)
        self.assertIn("not a paper execution of s1", english.lower())

    def test_claim_docs_name_discrimination_without_paper_s1(self) -> None:
        text = ORACLE_CLAIM.read_text(encoding="utf-8")
        self.assertIn("rejects known-bad probes", text)
        self.assertIn("not a proof of accounting correctness", text)
        self.assertIn("Django ORM and SQL are not executed", text)
        self.assertIn("golden echo", text.lower())
        self.assertIn(PIN, text)

    def test_ci_has_a_discrimination_job(self) -> None:
        text = ORACLE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3.12 subjects/django-accounting/oracle.py", text)
        self.assertIn(EXPECTED_OK, text)
        self.assertIn("python3.12 subjects/django-accounting/check-discrimination.py", text)
        self.assertIn("discrimination:", text)
        self.assertNotIn("cases=19", text)


if __name__ == "__main__":
    unittest.main()
