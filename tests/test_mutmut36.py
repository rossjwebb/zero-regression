# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.mutmut36 import rows_from_mutants_dir


class Mutmut36AdapterTests(unittest.TestCase):
    def test_six_outcome_mappings_from_meta(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mutants = Path(temporary) / "mutants"
            mutants.mkdir()
            (mutants / "mod.py.meta").write_text(
                json.dumps(
                    {
                        "exit_code_by_key": {
                            "mod.xǁClsǁfn__mutmut_1": 1,
                            "mod.xǁClsǁfn__mutmut_2": 0,
                            "mod.xǁClsǁfn__mutmut_3": 36,
                            "mod.xǁClsǁfn__mutmut_4": 35,
                            "mod.xǁClsǁfn__mutmut_5": 34,
                            "mod.xǁClsǁfn__mutmut_6": 33,
                        },
                        "type_check_error_by_key": {},
                        "durations_by_key": {},
                        "estimated_durations_by_key": {},
                    }
                ),
                encoding="utf-8",
            )
            rows, source = rows_from_mutants_dir(mutants)
            self.assertEqual(source, "meta")
            outcomes = {row["mutant_id"]: row["outcome"] for row in rows}
            self.assertEqual(
                outcomes,
                {
                    "1": "KILLED",
                    "2": "SURVIVED",
                    "3": "TIMEOUT",
                    "4": "SUSPICIOUS",
                    "5": "SKIPPED",
                    "6": "SKIPPED",
                },
            )
            self.assertEqual(rows[0]["operator"], "mutmut_1")
            self.assertIn("mod.Cls.fn", rows[0]["location"])
            self.assertEqual(rows[0]["mutmut_key"], "mod.xǁClsǁfn__mutmut_1")


if __name__ == "__main__":
    unittest.main()
