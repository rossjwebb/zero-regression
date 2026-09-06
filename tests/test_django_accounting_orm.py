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
STAGE_D = SUBJECT / "check-stage-d.py"
GATE = SUBJECT / "check-orm.py"
RUNNER = SUBJECT / "orm" / "run-org-aggregates.py"
WRITE_LOCK = SUBJECT / "orm" / "write-lock.py"
POSTURE = SUBJECT / "evidence" / "orm" / "posture.json"
ENGLISH = SUBJECT / "evidence" / "orm" / "EVIDENCE.md"
ORACLE_CLAIM = SUBJECT / "ORACLE.md"
PROGRAMME = REPO / "PROGRAMME.md"
README = REPO / "README.md"
SUBJECT_README = SUBJECT / "README.md"
PARENT_EVIDENCE = SUBJECT / "evidence" / "EVIDENCE.md"
GOLDEN = SUBJECT / "golden" / "expected.json"
STUBS = SUBJECT / "stubs"
LEGACY_MANAGERS = SUBJECT / "legacy" / "accounting" / "apps" / "books" / "managers.py"
ORACLE_WORKFLOW = REPO / ".github" / "workflows" / "s1-django-accounting-oracle.yml"
ORM_WORKFLOW = REPO / ".github" / "workflows" / "s1-django-accounting-orm.yml"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_OK = f"ORACLE OK pin={PIN} cases=27 replay-only"
EXPECTED_ORM = (
    f"S1 ORM OK pin={PIN} django=5.2.17 "
    "path=pin-managers-queryset-aggregate "
    "paper_s1=unexecuted mutation_score=not-stored"
)
SQL_BACKED = ("organization_derived", "overdue_total")


class DjangoAccountingOrmTests(unittest.TestCase):
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
        self.assertIn("known_bad_rejected=3", result.stdout)

    def test_stage_d_is_still_green(self) -> None:
        result = subprocess.run(
            [sys.executable, str(STAGE_D)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("STAGE D OK", result.stdout)
        self.assertIn("paper_s1=unexecuted", result.stdout)
        self.assertIn("mutation_score=not-stored", result.stdout)

    def test_lock_is_consistent(self) -> None:
        result = subprocess.run(
            [sys.executable, str(WRITE_LOCK), "--check"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S1 ORM LOCK OK", result.stdout)
        self.assertIn("mutation_score=not-stored", result.stdout)

    def test_org_aggregates_issue_sum_sql(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RUNNER)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(lines[0], EXPECTED_ORM)
        receipt = json.loads("\n".join(lines[1:]))
        self.assertIs(receipt["orm_sql_executed"], True)
        self.assertEqual(receipt["paper_s1"], "unexecuted")
        self.assertEqual(receipt["mutation_score"], "not-stored")
        self.assertIs(receipt["pin_models_imported"], False)
        self.assertIs(receipt["legacy_edited"], False)
        self.assertIs(receipt["golden_widened"], False)
        self.assertIn("urlresolvers", receipt["pin_models_blocked"])
        self.assertTrue(receipt["sql"])
        self.assertTrue(any("SUM(" in statement.upper() for statement in receipt["sql"]))
        self.assertTrue(any("date_dued" in statement for statement in receipt["sql"]))
        self.assertEqual(receipt["results"]["org_turnover_excl_tax"], "307.00")
        self.assertEqual(receipt["results"]["other_turnover_excl_tax"], "1000.00")
        self.assertEqual(receipt["results"]["empty_turnover_excl_tax"], "0.00")
        self.assertEqual(receipt["results"]["org_overdue_total"], "12.00")
        self.assertIn("accounting.apps.books.managers.InvoiceQuerySet", receipt["queryset_class"])
        self.assertNotIn("kill_rate", receipt)

    def test_orm_gate_is_green_and_score_free(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GATE)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith(EXPECTED_OK + "\n"), result.stdout)
        self.assertIn(EXPECTED_ORM, result.stdout)
        self.assertIn("S1 ORM POSTURE OK", result.stdout)
        self.assertIn("paper_s1=unexecuted", result.stdout)
        self.assertIn("mutation_score=not-stored", result.stdout)
        self.assertIn("orm_sql_executed=true", result.stdout)
        self.assertIn("blocked=pin-models-django-1.7-apis", result.stdout)
        self.assertNotIn("killed/seeded", result.stdout.lower())
        self.assertNotIn("kill rate", result.stdout.lower())

    def test_stub_still_has_no_aggregate(self) -> None:
        import importlib.util

        stub_models = STUBS / "django" / "db" / "models" / "__init__.py"
        spec = importlib.util.spec_from_file_location("s1_stub_django_db_models", stub_models)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertFalse(hasattr(module.QuerySet, "aggregate"))
        self.assertFalse(hasattr(module.RelatedManager, "turnover_excl_tax"))

    def test_golden_was_not_widened(self) -> None:
        payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["cases"]), 27)
        for name in SQL_BACKED:
            self.assertNotIn(name, payload["cases"])

    def test_legacy_managers_are_unedited(self) -> None:
        text = LEGACY_MANAGERS.read_text(encoding="utf-8")
        self.assertIn("return self.aggregate(sum=Sum(prop))[\"sum\"]", text)
        self.assertIn("def turnover_excl_tax(self):", text)
        self.assertIn("def debts_excl_tax(self):", text)
        self.assertIn("return self.filter(date_dued__lte=date.today())", text)

    def test_posture_and_english_are_honest(self) -> None:
        payload = json.loads(POSTURE.read_text(encoding="utf-8"))
        self.assertEqual(payload["paper_s1"], "unexecuted")
        self.assertEqual(payload["mutation_score"], "not-stored")
        self.assertIs(payload["orm_sql_executed"], True)
        self.assertIs(payload["pin_models_imported"], False)
        self.assertIs(payload["golden_widened"], False)
        self.assertIs(payload["legacy_edited"], False)
        self.assertEqual(payload["path"], "pin-managers-queryset-aggregate")
        self.assertEqual(payload["blocked"], "pin-models-django-1.7-apis")
        self.assertNotIsInstance(payload["mutation_score"], (int, float))
        self.assertNotIn("kill_rate", payload)
        english = ENGLISH.read_text(encoding="utf-8")
        self.assertIn("paper_s1=unexecuted", english)
        self.assertIn("mutation_score=not-stored", english)
        self.assertIn("not paper S1", english)
        self.assertIn("pin-managers-queryset-aggregate", english)
        self.assertNotIn("paper s1 ran", english.lower())

    def test_docs_name_orm_path_without_paper_s1(self) -> None:
        for path in (ORACLE_CLAIM, PROGRAMME, README, SUBJECT_README, PARENT_EVIDENCE):
            text = path.read_text(encoding="utf-8")
            self.assertIn("org-level", text.lower(), path)
            self.assertIn("not paper s1", text.lower(), path)

    def test_ci_runs_orm_and_does_not_skip_discrimination(self) -> None:
        self.assertTrue(ORM_WORKFLOW.is_file())
        workflow = ORM_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3.12 subjects/django-accounting/oracle.py", workflow)
        self.assertIn("python3.12 subjects/django-accounting/check-discrimination.py", workflow)
        self.assertIn("python3.12 subjects/django-accounting/check-stage-d.py", workflow)
        self.assertIn("python3.12 subjects/django-accounting/check-orm.py", workflow)
        self.assertIn("--require-hashes", workflow)
        self.assertIn(EXPECTED_OK, workflow)
        self.assertNotIn("cases=19", workflow)
        oracle_workflow = ORACLE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3.12 subjects/django-accounting/check-orm.py", oracle_workflow)
        self.assertIn("check-discrimination.py", oracle_workflow)
        self.assertIn("check-stage-d.py", oracle_workflow)
        self.assertNotIn("exit 0", oracle_workflow)


if __name__ == "__main__":
    unittest.main()
