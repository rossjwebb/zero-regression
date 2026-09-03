# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "django-accounting"
ORACLE = SUBJECT / "oracle.py"
ORACLE_CLAIM = SUBJECT / "ORACLE.md"
GOLDEN = SUBJECT / "golden" / "expected.json"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
SQL_BACKED_CASES = ("organization_derived", "overdue_total")


class DjangoAccountingOracleTests(unittest.TestCase):
    def test_oracle_matches_golden_file(self) -> None:
        result = subprocess.run([sys.executable, str(ORACLE)], cwd=REPO, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(PIN, result.stdout)
        self.assertIn("replay-only", result.stdout)

    def test_golden_file_records_the_pin_and_the_claim(self) -> None:
        payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertEqual(payload["pin"], PIN)
        self.assertIn("not a proof of accounting correctness", payload["claim"])
        self.assertIn("Django ORM and SQL are not executed", payload["claim"])
        self.assertGreaterEqual(len(payload["cases"]), 19)
        for name in SQL_BACKED_CASES:
            self.assertNotIn(name, payload["cases"])
        for name in (
            "price_unknown_tax_access",
            "price_tax_zero",
            "time_interval",
            "invoice_half_quantity",
            "payment_allocation_partial",
            "profits_empty_organization",
            "profits_dated_invoice_only",
            "calculator_rejects_unknown_sum_type",
        ):
            self.assertIn(name, payload["cases"])

    def test_claim_is_documented_next_to_the_oracle(self) -> None:
        text = ORACLE_CLAIM.read_text(encoding="utf-8")
        self.assertIn("not a proof of accounting correctness", text)
        self.assertIn("Django ORM and SQL are not executed", text)
        self.assertIn(PIN, text)

    def test_stub_does_not_implement_orm_sql(self) -> None:
        stubs = SUBJECT / "stubs"
        if str(stubs) not in sys.path:
            sys.path.insert(0, str(stubs))
        from django.db.models import QuerySet, RelatedManager

        self.assertFalse(hasattr(QuerySet, "aggregate"))
        self.assertFalse(hasattr(QuerySet, "dued"))
        self.assertFalse(hasattr(QuerySet, "turnover_excl_tax"))
        self.assertFalse(hasattr(QuerySet, "total_paid"))
        self.assertFalse(hasattr(RelatedManager, "turnover_excl_tax"))
        self.assertFalse(hasattr(RelatedManager, "dued"))
        items = QuerySet([type("Row", (), {"organization": "keep", "other": 1})()])
        filtered = items.filter(organization="missing", payments__date_paid__gte="ignored")
        self.assertEqual(len(filtered), 1)

    def test_tampered_golden_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tampered = Path(temporary) / "expected.json"
            tampered.write_text(GOLDEN.read_text(encoding="utf-8").replace('"10.00"', '"10.01"', 1), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ORACLE), "--golden", str(tampered)], cwd=REPO, capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ORACLE FAILURE", result.stderr)


if __name__ == "__main__":
    unittest.main()
