# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest
from pathlib import Path

from zero_regression_harness.cli import main, verify_command

REPO = Path(__file__).resolve().parents[1]
FIXTURES = (
    REPO / "fixtures" / "accounting-service" / "evidence.jsonl",
    REPO / "fixtures" / "accounting-service" / "pre-remediation" / "evidence.jsonl",
    REPO / "fixtures" / "accounting-service" / "superseded" / "publish-4" / "evidence.jsonl",
)


class CliVerifyTests(unittest.TestCase):
    def test_retained_fixture_chains_exit_0(self) -> None:
        for log in FIXTURES:
            with self.subTest(log=str(log.relative_to(REPO))):
                self.assertEqual(verify_command(log), 0)
                self.assertEqual(main(["verify", str(log)]), 0)


if __name__ == "__main__":
    unittest.main()
