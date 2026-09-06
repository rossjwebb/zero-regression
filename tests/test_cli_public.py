# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
import subprocess
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from zero_regression_harness.cli import main, verify_command
from zero_regression_harness.public_subjects import (
    S1_ORACLE_OK,
    certify_s1,
    certify_s2,
    certify_s3,
    protocol_for,
    resolve_subject,
    score_errors,
    verify_s1,
    verify_s2,
    verify_s3,
)

REPO = Path(__file__).resolve().parents[1]
S1 = REPO / "subjects" / "django-accounting"
S2 = REPO / "subjects" / "commons-csv"
S3 = REPO / "subjects" / "carddemo"
FIXTURE = REPO / "fixtures" / "accounting-service" / "evidence.jsonl"
PROGRAMME = REPO / "PROGRAMME.md"
README = REPO / "README.md"
PR_CHECKS = REPO / ".github" / "workflows" / "pr-checks.yml"
S1_ORM_WORKFLOW = REPO / ".github" / "workflows" / "s1-django-accounting-orm.yml"
S2_WORKFLOW = REPO / ".github" / "workflows" / "s2-commons-csv.yml"
S3_WORKFLOW = REPO / ".github" / "workflows" / "s3-carddemo-compile.yml"


def _completed(command: list[str], returncode: int, stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout, "")


class PublicSubjectResolveTests(unittest.TestCase):
    def test_aliases_and_paths_resolve(self) -> None:
        self.assertEqual(resolve_subject("s1"), S1.resolve())
        self.assertEqual(resolve_subject("s2"), S2.resolve())
        self.assertEqual(resolve_subject("s3"), S3.resolve())
        self.assertEqual(resolve_subject(S1), S1.resolve())
        self.assertEqual(resolve_subject("subjects/commons-csv"), S2.resolve())
        self.assertEqual(protocol_for(S1), "s1")
        self.assertEqual(protocol_for(S2), "s2")
        self.assertEqual(protocol_for(S3), "s3")
        self.assertEqual(protocol_for(REPO / "subjects" / "accounting-service"), "mutmut")


class PublicVerifyTests(unittest.TestCase):
    def test_fixture_chain_still_verifies(self) -> None:
        self.assertEqual(verify_command(FIXTURE), 0)
        self.assertEqual(main(["verify", str(FIXTURE)]), 0)

    def test_public_subjects_verify_score_free(self) -> None:
        for target, needle in (
            (S1, "paper_s1=unexecuted"),
            (S2, "paper_s2=unexecuted"),
            (S3, "posttran_job=not-run"),
            ("s1", "S1 posture"),
            ("s2", "mutation_score=not-stored"),
            ("s3", "mutation_score=not-stored"),
        ):
            with self.subTest(target=str(target)):
                captured = io.StringIO()
                with redirect_stdout(captured):
                    self.assertEqual(main(["verify", str(target)]), 0)
                self.assertIn(needle, captured.getvalue())
                self.assertNotIn("killed/seeded", captured.getvalue().lower())

        s1_errors, _ = verify_s1(S1)
        s2_errors, _ = verify_s2(S2)
        s3_errors, _ = verify_s3(S3)
        self.assertEqual(s1_errors, [])
        self.assertEqual(s2_errors, [])
        self.assertEqual(s3_errors, [])

    def test_accounting_service_directory_is_not_a_public_verify(self) -> None:
        self.assertEqual(main(["verify", "subjects/accounting-service"]), 1)

    def test_numeric_score_is_rejected(self) -> None:
        errors = score_errors({"mutation_score": 91.0, "kill_rate": 12})
        self.assertTrue(any("must not be numeric" in item for item in errors), errors)


class PublicCertifyTests(unittest.TestCase):
    def test_s2_certify_is_score_free(self) -> None:
        captured = io.StringIO()
        with redirect_stdout(captured):
            code = certify_s2(S2)
        self.assertEqual(code, 0)
        self.assertIn("mutation_score=not-stored", captured.getvalue())
        self.assertIn("CERTIFY S2 OK", captured.getvalue())
        self.assertNotIn("killed/seeded", captured.getvalue().lower())
        self.assertNotRegex(captured.getvalue(), r"\b\d+(\.\d+)?%")
        self.assertEqual(main(["certify", "s2"]), 0)

    def test_s1_certify_runs_existing_gates(self) -> None:
        outputs = {
            "oracle.py": (0, S1_ORACLE_OK + "\n"),
            "check-discrimination.py": (0, S1_ORACLE_OK + "\nDISCRIMINATION OK paper_s1=unexecuted\n"),
            "check-stage-d.py": (0, "STAGE D OK paper_s1=unexecuted mutation_score=not-stored\n"),
            "check-orm.py": (0, "S1 ORM POSTURE OK paper_s1=unexecuted mutation_score=not-stored\n"),
        }

        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            name = Path(command[-1]).name
            code, stdout = outputs[name]
            return _completed(command, code, stdout)

        with mock.patch("zero_regression_harness.public_subjects.run_process", side_effect=fake_run):
            self.assertEqual(certify_s1(S1), 0)

    def test_s1_missing_orm_is_fail_closed(self) -> None:
        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            name = Path(command[-1]).name
            if name == "check-orm.py":
                return _completed(command, 2, "S1 ORM FAIL-CLOSED: Django missing\n")
            if name == "oracle.py":
                return _completed(command, 0, S1_ORACLE_OK + "\n")
            return _completed(command, 0, "DISCRIMINATION OK\nSTAGE D OK\n")

        with mock.patch("zero_regression_harness.public_subjects.run_process", side_effect=fake_run):
            self.assertEqual(certify_s1(S1), 2)

    def test_s3_compile_ok_exits_2_and_does_not_claim_posttran(self) -> None:
        work = S3 / "work"
        work.mkdir(exist_ok=True)
        receipt = work / "COMPILE"

        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if command[-1].endswith("check-pins.py"):
                return _completed(command, 0, "S3 PIN OK carddemo=59cc6c2fd7eb slice=POSTTRAN/CBTRN02C\n")
            receipt.write_text(
                "\n".join(
                    [
                        "result=compile-ok",
                        "cobc_status=0",
                        "harness_exit=2",
                        "harness_meaning=posttran-job-not-run",
                        "posttran_job=not-run",
                        "mutation_score=not-recorded",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            return _completed(
                command,
                2,
                "S3 COMPILE OK: compile only\nS3 HARNESS EXIT 2: posttran_job=not-run\n",
            )

        try:
            with mock.patch("zero_regression_harness.public_subjects.run_process", side_effect=fake_run):
                self.assertEqual(certify_s3(S3), 2)
        finally:
            if receipt.is_file():
                receipt.unlink()

    def test_s3_exit_0_is_fail_closed(self) -> None:
        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if command[-1].endswith("check-pins.py"):
                return _completed(command, 0, "S3 PIN OK carddemo=59cc6c2fd7eb\n")
            return _completed(command, 0, "S3 COMPILE OK\n")

        with mock.patch("zero_regression_harness.public_subjects.run_process", side_effect=fake_run):
            self.assertEqual(certify_s3(S3), 2)

    def test_s3_cobc_fail_is_not_job_not_run_success(self) -> None:
        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if command[-1].endswith("check-pins.py"):
                return _completed(command, 0, "S3 PIN OK carddemo=59cc6c2fd7eb\n")
            return _completed(command, 2, "S3 COBC FAIL: pinned cobc exited 1\n")

        with mock.patch("zero_regression_harness.public_subjects.run_process", side_effect=fake_run):
            self.assertEqual(certify_s3(S3), 1)

    def test_s2_and_s3_certify_do_not_write_mutmut_chains(self) -> None:
        evidence_runs = list((S2 / "evidence").glob("run-*")) + list((S3 / "evidence").glob("run-*"))
        self.assertEqual(evidence_runs, [])


class PublicDocsAndCiTests(unittest.TestCase):
    def test_docs_name_certify_coverage_honestly(self) -> None:
        for path in (PROGRAMME, README):
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            self.assertIn("zero-regression certify", lowered, path)
            self.assertIn("mutation_score=not-stored", text.replace("`", ""), path)
            self.assertIn("posttran_job=not-run", text.replace("`", ""), path)
            self.assertIn("not paper s1", lowered, path)
            self.assertIn("not paper s2", lowered, path)
            self.assertIn("not paper s3", lowered, path)
            self.assertIn("does not invent a mutation score", lowered, path)

    def test_ci_wires_public_certify(self) -> None:
        pr_checks = PR_CHECKS.read_text(encoding="utf-8")
        self.assertIn("zero-regression verify subjects/django-accounting", pr_checks)
        self.assertIn("zero-regression verify subjects/commons-csv", pr_checks)
        self.assertIn("zero-regression verify subjects/carddemo", pr_checks)
        self.assertIn("zero-regression certify subjects/commons-csv", pr_checks)
        self.assertIn("tests.test_cli_public", pr_checks)
        self.assertIn("zero-regression certify subjects/django-accounting", S1_ORM_WORKFLOW.read_text(encoding="utf-8"))
        self.assertIn("zero-regression certify subjects/commons-csv", S2_WORKFLOW.read_text(encoding="utf-8"))
        s3 = S3_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("zero-regression certify subjects/carddemo", s3)
        self.assertIn("CERTIFY S3 COMPILE OK", s3)
        self.assertIn("posttran_job=not-run", s3)


if __name__ == "__main__":
    unittest.main()
