# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "django-accounting"
EVIDENCE = SUBJECT / "evidence"
POSTURE = EVIDENCE / "s1-part-b-posture.json"
ENGLISH = EVIDENCE / "EVIDENCE.md"
GATE = SUBJECT / "check-part-b.py"
ORACLE = SUBJECT / "oracle.py"
GOLDEN = SUBJECT / "golden" / "expected.json"
RECEIPT_SCRIPT = EVIDENCE / "arms" / "run-arm-oracle.py"
ORACLE_WORKFLOW = REPO / ".github" / "workflows" / "s1-django-accounting-oracle.yml"
PART_B_WORKFLOW = REPO / ".github" / "workflows" / "s1-django-accounting-part-b.yml"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_OK = f"ORACLE OK pin={PIN} cases=27 replay-only"
EXPECTED_STATUS = "three-arms-executed"
ARM_KEYS = ("cursor", "claude_code", "gemini")
ARM_DIRS = ("cursor", "claude-code", "gemini")
EXECUTED_DIRS = ("cursor", "claude-code", "gemini")


class DjangoAccountingPartBTests(unittest.TestCase):
    def test_oracle_stdout_is_exactly_the_replay_only_line(self) -> None:
        result = subprocess.run([sys.executable, str(ORACLE)], cwd=REPO, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED_OK + "\n")

    def test_part_b_gate_requires_the_same_oracle_line(self) -> None:
        result = subprocess.run([sys.executable, str(GATE)], cwd=REPO, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith(EXPECTED_OK + "\n"), result.stdout)
        self.assertIn("S1 PART B POSTURE OK", result.stdout)
        self.assertIn("paper_s1=unexecuted", result.stdout)
        self.assertIn("oracle=replay-only", result.stdout)
        self.assertIn("mutation_score=not-stored", result.stdout)
        self.assertIn("codex_arm=omitted", result.stdout)
        self.assertIn("cursor=executed", result.stdout)
        self.assertIn("claude_code=executed", result.stdout)
        self.assertIn("gemini=executed", result.stdout)
        self.assertIn("generators_run=cursor+claude+gemini", result.stdout)
        self.assertIn("three_arm_comparison=available-thin-oracle", result.stdout)
        self.assertNotIn("claude_code=awaiting-external-run", result.stdout)
        self.assertNotIn("gemini=awaiting-external-run", result.stdout)
        self.assertNotIn("cases=19", result.stdout)
        self.assertNotIn("killed/seeded", result.stdout.lower())

    def test_honesty_claim_fields(self) -> None:
        self.assertTrue(POSTURE.is_file())
        self.assertTrue(ENGLISH.is_file())
        payload = json.loads(POSTURE.read_text(encoding="utf-8"))
        self.assertEqual(payload["paper_s1"], "unexecuted")
        self.assertEqual(payload["oracle"], "replay-only")
        self.assertEqual(payload["cases"], 27)
        self.assertEqual(payload["pin"], PIN)
        self.assertIs(payload["import_only_stub"], True)
        self.assertEqual(payload["mutation_score"], "not-stored")
        self.assertEqual(payload["domain_correctness"], "out_of_scope")
        self.assertEqual(payload["codex_arm"], "omitted")
        self.assertTrue(payload["codex_omission_reason"])
        self.assertEqual(payload["status"], EXPECTED_STATUS)
        self.assertEqual(payload["three_arm_comparison"], "available")
        self.assertIn("too thin to discriminate", payload["three_arm_comparison_reading"])
        self.assertEqual(payload["oracle_gate"]["stdout"], EXPECTED_OK)
        claims = payload["claims"]
        self.assertEqual(claims["paper_s1"], "unexecuted")
        self.assertEqual(claims["oracle"], "replay-only")
        self.assertEqual(claims["cases"], 27)
        self.assertEqual(claims["pin"], PIN)
        self.assertIs(claims["import_only_stub"], True)
        self.assertEqual(claims["mutation_score"], "not-stored")
        self.assertEqual(claims["domain_correctness"], "out_of_scope")
        self.assertEqual(claims["codex_arm"], "omitted")
        self.assertEqual(claims["status"], EXPECTED_STATUS)
        self.assertIs(claims["generators_run"], True)

    def test_rejects_numeric_mutation_score(self) -> None:
        payload = json.loads(POSTURE.read_text(encoding="utf-8"))
        self.assertNotIsInstance(payload["mutation_score"], (int, float))
        self.assertIsInstance(payload["mutation_score"], str)
        self.assertNotIsInstance(payload["claims"]["mutation_score"], (int, float))
        self._assert_no_numeric_mutation_score(payload)
        for name in ARM_DIRS:
            slot = json.loads((EVIDENCE / "arms" / name / "arm.json").read_text(encoding="utf-8"))
            self._assert_no_numeric_mutation_score(slot)
            self.assertNotIn("kill_rate", slot)
        spec = importlib.util.spec_from_file_location("s1_part_b_gate", GATE)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tampered = json.loads(POSTURE.read_text(encoding="utf-8"))
        tampered["mutation_score"] = 91.0
        errors = module.check_honesty(tampered)
        self.assertTrue(any("mutation_score" in error for error in errors), errors)

    def test_three_arms_only_and_honest_statuses(self) -> None:
        payload = json.loads(POSTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(payload["arms"]), set(ARM_KEYS))
        self.assertEqual(set(payload["generators_run"]), set(ARM_KEYS))
        self.assertNotIn("codex", payload["arms"])
        self.assertFalse((EVIDENCE / "arms" / "codex").exists())
        self.assertIs(payload["generators_run"]["cursor"], True)
        self.assertIs(payload["generators_run"]["claude_code"], True)
        self.assertIs(payload["generators_run"]["gemini"], True)
        self.assertEqual(payload["arms"]["cursor"]["status"], "executed")
        self.assertIs(payload["arms"]["cursor"]["generators_run"], True)
        self.assertEqual(payload["arms"]["claude_code"]["status"], "executed")
        self.assertEqual(payload["arms"]["gemini"]["status"], "executed")
        self.assertIs(payload["arms"]["claude_code"]["generators_run"], True)
        self.assertIs(payload["arms"]["gemini"]["generators_run"], True)
        self.assertEqual(payload["certificate"]["executed_arms"], ["cursor", "claude_code", "gemini"])
        self.assertEqual(payload["certificate"]["awaiting_external_arms"], [])
        self.assertEqual(payload["posture_gate"]["executed_arms"], ["cursor", "claude_code", "gemini"])
        self.assertEqual(payload["posture_gate"]["awaiting_external_arms"], [])
        for name in EXECUTED_DIRS:
            slot = json.loads((EVIDENCE / "arms" / name / "arm.json").read_text(encoding="utf-8"))
            self.assertEqual(slot["status"], "executed")
            self.assertIs(slot["generators_run"], True)
            self.assertEqual(slot["oracle"]["stdout"], EXPECTED_OK)
            self.assertEqual(slot["oracle"]["match_count"], 27)
            self.assertEqual(slot["oracle"]["mismatch_count"], 0)
            self.assertEqual(slot["oracle"]["exit"], 0)
            self.assertIs(slot["candidate_artefacts"]["produced"], False)
            self.assertEqual(slot["zero_mismatch_means"], "oracle too thin to discriminate")
            self.assertIn("four clean generators", slot["zero_mismatch_does_not_mean"])
            receipt = json.loads((EVIDENCE / "arms" / name / "oracle-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["stdout"], EXPECTED_OK)
            self.assertEqual(receipt["match_count"], 27)
            self.assertEqual(receipt["mismatch_count"], 0)
        claude = json.loads((EVIDENCE / "arms" / "claude-code" / "arm.json").read_text(encoding="utf-8"))
        self.assertEqual(claude["arm"], "claude_code")
        self.assertEqual(claude["name"], "Claude Code")
        self.assertEqual(
            claude["prompt"],
            (EVIDENCE / "arms" / "claude-code" / "PROMPT.md").read_text(encoding="utf-8"),
        )
        self.assertIn("not a second Cursor arm", claude["method"])
        self.assertIn("not a Claude · Max chat run", claude["method"])
        self.assertIn("run-arm-oracle.py", claude["method"])
        self.assertIn("Python 3.12.3", claude["method"])
        self.assertIn("produced=false", claude["method"])
        gemini = json.loads((EVIDENCE / "arms" / "gemini" / "arm.json").read_text(encoding="utf-8"))
        self.assertEqual(gemini["arm"], "gemini")
        self.assertEqual(gemini["name"], "Gemini")
        self.assertEqual(
            gemini["prompt"],
            (EVIDENCE / "arms" / "gemini" / "PROMPT.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(gemini["executed_at"], "2026-09-06T07:11:37Z")
        self.assertIn("Numbers copied from the receipt only", gemini["method"])

    def test_rejects_invented_external_oracle_results(self) -> None:
        spec = importlib.util.spec_from_file_location("s1_part_b_gate", GATE)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fake = {
            "status": "awaiting-external-run",
            "generators_run": False,
            "reason": "synthetic awaiting slot for the invented-result guard",
            "prompt": (EVIDENCE / "arms" / "gemini" / "PROMPT.md").read_text(encoding="utf-8"),
            "script": "subjects/django-accounting/evidence/arms/run-arm-oracle.py",
            "oracle": {"stdout": EXPECTED_OK, "match_count": 27, "mismatch_count": 0, "exit": 0},
        }
        errors = module.check_external_slot("gemini", fake)
        self.assertTrue(any("invented" in error for error in errors), errors)

    def test_shared_receipt_script_matches_live_oracle(self) -> None:
        self.assertTrue(RECEIPT_SCRIPT.is_file())
        result = subprocess.run([sys.executable, str(RECEIPT_SCRIPT)], cwd=REPO, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["stdout"], EXPECTED_OK)
        self.assertEqual(receipt["match_count"], 27)
        self.assertEqual(receipt["mismatch_count"], 0)
        self.assertEqual(receipt["exit"], 0)
        self.assertEqual(receipt["python"], "3.12.3")
        self.assertEqual(receipt["mutation_score"], "not-stored")
        for name in EXECUTED_DIRS:
            stored = json.loads((EVIDENCE / "arms" / name / "oracle-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["stdout"], receipt["stdout"])
            self.assertEqual(stored["match_count"], receipt["match_count"])
            self.assertEqual(stored["mismatch_count"], receipt["mismatch_count"])

    def test_certificate_language(self) -> None:
        payload = json.loads(POSTURE.read_text(encoding="utf-8"))
        certificate = payload["certificate"]
        self.assertEqual(certificate["oracle"], "replay-only")
        self.assertEqual(certificate["recorded_traces"], 27)
        self.assertEqual(certificate["domain_correctness"], "out_of_scope")
        self.assertEqual(certificate["zero_mismatch_means"], "oracle too thin to discriminate")
        self.assertIn("four clean generators", certificate["zero_mismatch_does_not_mean"])
        self.assertIn("success theatre", certificate["zero_mismatch_does_not_mean"])
        english = ENGLISH.read_text(encoding="utf-8")
        self.assertIn("paper_s1=unexecuted", english)
        self.assertIn("oracle=replay-only", english)
        self.assertIn("cases=27", english)
        self.assertIn(PIN, english)
        self.assertIn("import_only_stub=true", english)
        self.assertIn("mutation_score=not-stored", english)
        self.assertIn("domain_correctness=out_of_scope", english)
        self.assertIn("codex_arm=omitted", english)
        self.assertIn("27 recorded traces", english)
        self.assertIn("domain correctness is out of scope", english)
        self.assertIn("too thin to discriminate", english)
        self.assertIn("four clean generators", english)
        self.assertIn("success theatre", english)
        self.assertIn("three-arms-executed", english)
        self.assertIn("not a paper execution of s1", english.lower())
        self.assertNotIn("four clean generators succeeded", english.lower())

    def test_golden_file_is_still_the_27_trace_slice(self) -> None:
        payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertEqual(payload["pin"], PIN)
        self.assertEqual(len(payload["cases"]), 27)

    def test_existing_oracle_workflow_is_not_weakened(self) -> None:
        text = ORACLE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3.12 subjects/django-accounting/oracle.py", text)
        self.assertIn(EXPECTED_OK, text)
        self.assertNotIn("exit 0", text)
        self.assertNotIn("cases=19", text)

    def test_part_b_workflow_still_requires_oracle_stdout(self) -> None:
        self.assertTrue(PART_B_WORKFLOW.is_file())
        text = PART_B_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3.12 subjects/django-accounting/oracle.py", text)
        self.assertIn("python3.12 subjects/django-accounting/check-part-b.py", text)
        self.assertIn("python3.12 subjects/django-accounting/evidence/arms/run-arm-oracle.py", text)
        self.assertIn(EXPECTED_OK, text)
        self.assertIn("tests.test_django_accounting_part_b", text)
        self.assertNotIn("exit 0", text)

    def _assert_no_numeric_mutation_score(self, node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "mutation_score":
                    self.assertFalse(isinstance(value, (int, float)), value)
                    self.assertIn(value, ("not-stored", None))
                if key in {"kill_rate", "killed", "seeded", "survivors"}:
                    self.assertFalse(isinstance(value, (int, float)), value)
                self._assert_no_numeric_mutation_score(value)
        elif isinstance(node, list):
            for item in node:
                self._assert_no_numeric_mutation_score(item)


if __name__ == "__main__":
    unittest.main()
