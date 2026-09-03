# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "commons-csv"
if str(SUBJECT) not in sys.path:
    sys.path.insert(0, str(SUBJECT))

from toolchain import JAVA8_MAJOR, judge_pit_log  # noqa: E402


class CommonsCsvToolchainTests(unittest.TestCase):
    def test_timeout_zero_is_not_a_failure(self) -> None:
        log = (
            "> org.pitest.mutationtest.engine.gregor.mutators.MathMutator\n"
            "> KILLED 1 SURVIVED 0 TIMED_OUT 0 NON_VIABLE 0\n"
            "> MEMORY_ERROR 0 NOT_STARTED 0 STARTED 0 RUN_ERROR 0\n"
        )
        self.assertEqual(judge_pit_log(log), [])

    def test_timed_out_mutant_fails_closed_without_a_score(self) -> None:
        log = (
            "PIT >> WARNING : Minion exited abnormally due to TIMED_OUT\n"
            "> KILLED 3 SURVIVED 0 TIMED_OUT 1 NON_VIABLE 0\n"
            "> MEMORY_ERROR 0 NOT_STARTED 0 STARTED 0 RUN_ERROR 0\n"
            ">> Generated 34 mutations Killed 12 (35%)\n"
        )
        errors = judge_pit_log(log)
        self.assertTrue(any("TIMED_OUT" in error for error in errors))
        self.assertTrue(any("minion exited abnormally" in error.lower() for error in errors))
        joined = " ".join(errors).lower()
        self.assertNotIn("35%", joined)
        self.assertNotIn("killed/seeded", joined)

    def test_memory_error_fails_closed(self) -> None:
        log = "> KILLED 0 SURVIVED 0 TIMED_OUT 0 NON_VIABLE 0\n> MEMORY_ERROR 2 NOT_STARTED 0 STARTED 0 RUN_ERROR 0\n"
        errors = judge_pit_log(log)
        self.assertTrue(any("MEMORY_ERROR" in error for error in errors))

    def test_no_mutations_fails_closed(self) -> None:
        errors = judge_pit_log("No mutations found. This probably means there is an issue")
        self.assertTrue(errors)

    def test_minion_died_fails_closed(self) -> None:
        errors = judge_pit_log("Coverage generator Minion exited abnormally due to MINION_DIED")
        self.assertTrue(any("minion" in error.lower() for error in errors))

    def test_unrecognized_option_fails_closed(self) -> None:
        errors = judge_pit_log(">>>> excludedTests is not a recognized option")
        self.assertTrue(any("command line" in error for error in errors))

    def test_java8_classfile_major_is_documented(self) -> None:
        self.assertEqual(JAVA8_MAJOR, 52)
