# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ORACLE = REPO / "subjects" / "django-accounting" / "oracle.py"
GOLDEN = REPO / "subjects" / "django-accounting" / "golden" / "expected.json"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"


class DjangoAccountingOracleTests(unittest.TestCase):
    def test_oracle_matches_golden_file(self) -> None:
        result = subprocess.run([sys.executable, str(ORACLE)], cwd=REPO, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(PIN, result.stdout)

    def test_golden_file_records_the_pin(self) -> None:
        payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertEqual(payload["pin"], PIN)
        self.assertGreaterEqual(len(payload["cases"]), 15)

    def test_tampered_golden_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tampered = Path(temporary) / "expected.json"
            tampered.write_text(GOLDEN.read_text(encoding="utf-8").replace('"10.00"', '"10.01"', 1), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ORACLE), "--golden", str(tampered)], cwd=REPO, capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ORACLE FAILURE", result.stderr)


if __name__ == "__main__":
    unittest.main()
