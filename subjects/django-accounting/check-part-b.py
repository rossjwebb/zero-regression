#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""S1 Part B honesty gate for django-accounting.

Requires the existing replay-only oracle stdout exactly. Checks the
Part B posture pack: Cursor executed against that oracle; Claude Code
and Gemini awaiting an external run. Does not record a mutation
score. This is not paper S1.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SUBJECT = Path(__file__).resolve().parent
REPO = SUBJECT.parent.parent
ORACLE = SUBJECT / "oracle.py"
POSTURE = SUBJECT / "evidence" / "s1-part-b-posture.json"
EVIDENCE = SUBJECT / "evidence" / "EVIDENCE.md"
ARMS_DIR = SUBJECT / "evidence" / "arms"
RECEIPT_SCRIPT = ARMS_DIR / "run-arm-oracle.py"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_ORACLE = f"ORACLE OK pin={PIN} cases=27 replay-only"
EXPECTED_STATUS = "cursor-executed+external-awaiting"
ARM_KEYS = ("cursor", "claude_code", "gemini")
ARM_DIRS = ("cursor", "claude-code", "gemini")
RESULT_KEYS = ("match_count", "mismatch_count", "stdout", "exit")


def fail(message: str) -> int:
    print(f"S1 PART B FAIL-CLOSED: {message}", file=sys.stderr)
    return 2


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(fail(f"missing {path}"))
    return json.loads(path.read_text(encoding="utf-8"))


def load_posture() -> dict:
    return load_json(POSTURE)


def check_honesty(payload: dict) -> list[str]:
    errors: list[str] = []
    required = {
        "paper_s1": "unexecuted",
        "oracle": "replay-only",
        "cases": 27,
        "pin": PIN,
        "import_only_stub": True,
        "mutation_score": "not-stored",
        "domain_correctness": "out_of_scope",
        "codex_arm": "omitted",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            errors.append(f"{key}: expected {expected!r} got {payload.get(key)!r}")
    if payload.get("status") != EXPECTED_STATUS:
        errors.append(f"status: expected {EXPECTED_STATUS!r} got {payload.get('status')!r}")
    if isinstance(payload.get("mutation_score"), (int, float)):
        errors.append("mutation_score must not be numeric")
    claims = payload.get("claims")
    if not isinstance(claims, dict):
        errors.append("claims object is missing")
        return errors
    for key, expected in required.items():
        if claims.get(key) != expected:
            errors.append(f"claims.{key}: expected {expected!r} got {claims.get(key)!r}")
    if claims.get("status") != EXPECTED_STATUS:
        errors.append(f"claims.status: expected {EXPECTED_STATUS!r} got {claims.get('status')!r}")
    if claims.get("generators_run") is not False:
        errors.append("claims.generators_run must be false (three-arm set incomplete)")
    certificate = payload.get("certificate")
    if not isinstance(certificate, dict):
        errors.append("certificate object is missing")
    else:
        if certificate.get("oracle") != "replay-only":
            errors.append("certificate.oracle must be replay-only")
        if certificate.get("recorded_traces") != 27:
            errors.append("certificate.recorded_traces must be 27")
        if certificate.get("domain_correctness") != "out_of_scope":
            errors.append("certificate.domain_correctness must be out_of_scope")
        if certificate.get("zero_mismatch_means") != "oracle too thin to discriminate":
            errors.append("certificate must say zero mismatch means the oracle is too thin to discriminate")
        forbidden = certificate.get("zero_mismatch_does_not_mean") or []
        for phrase in ("four clean generators", "success theatre"):
            if phrase not in forbidden:
                errors.append(f"certificate must reject {phrase!r}")
    generators = payload.get("generators_run")
    if not isinstance(generators, dict):
        errors.append("generators_run object is missing")
    else:
        if set(generators) != set(ARM_KEYS):
            errors.append(f"generators_run keys must be {ARM_KEYS}, got {tuple(generators)}")
        expected_run = {"cursor": True, "claude_code": False, "gemini": False}
        for key, expected in expected_run.items():
            if generators.get(key) is not expected:
                errors.append(f"generators_run.{key} must be {expected}")
    arms = payload.get("arms")
    if not isinstance(arms, dict):
        errors.append("arms object is missing")
    else:
        if set(arms) != set(ARM_KEYS):
            errors.append(f"arms keys must be {ARM_KEYS}, got {tuple(arms)}")
        if "codex" in arms or "codex_arm" in arms:
            errors.append("Codex must not appear as an arm")
        expected_status = {
            "cursor": "executed",
            "claude_code": "awaiting-external-run",
            "gemini": "awaiting-external-run",
        }
        expected_run = {"cursor": True, "claude_code": False, "gemini": False}
        for key in ARM_KEYS:
            arm = arms.get(key) or {}
            if arm.get("status") != expected_status[key]:
                errors.append(f"arms.{key}.status must be {expected_status[key]!r}")
            if arm.get("generators_run") is not expected_run[key]:
                errors.append(f"arms.{key}.generators_run must be {expected_run[key]}")
    if not payload.get("codex_omission_reason"):
        errors.append("codex_omission_reason is missing")
    if payload.get("three_arm_comparison") != "not-available":
        errors.append("three_arm_comparison must be not-available")
    oracle_gate = payload.get("oracle_gate") or {}
    if oracle_gate.get("stdout") != EXPECTED_ORACLE:
        errors.append("oracle_gate.stdout must be the exact replay-only OK line")
    return errors


def _has_invented_result(payload: dict) -> list[str]:
    errors: list[str] = []
    if "oracle" in payload and isinstance(payload.get("oracle"), dict):
        oracle = payload["oracle"]
        for key in RESULT_KEYS:
            if key in oracle:
                errors.append(f"must not store invented oracle.{key}")
    for key in RESULT_KEYS:
        if key in payload:
            errors.append(f"must not store invented {key}")
    return errors


def check_arm_slots() -> list[str]:
    errors: list[str] = []
    if (ARMS_DIR / "codex").exists():
        errors.append("Codex arm directory must not exist")
    if not RECEIPT_SCRIPT.is_file():
        errors.append(f"missing shared probe {RECEIPT_SCRIPT}")
    for name in ARM_DIRS:
        path = ARMS_DIR / name / "arm.json"
        if not path.is_file():
            errors.append(f"missing arm slot {path}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "mutation_score" in payload and isinstance(payload["mutation_score"], (int, float)):
            errors.append(f"{name}: mutation_score must not be numeric")
        if "kill_rate" in payload and isinstance(payload["kill_rate"], (int, float)):
            errors.append(f"{name}: kill_rate must not be numeric")
        if name == "cursor":
            errors.extend(check_cursor_slot(payload))
        else:
            errors.extend(check_external_slot(name, payload))
    return errors


def check_cursor_slot(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("status") != "executed":
        errors.append("cursor: status must be executed")
    if payload.get("generators_run") is not True:
        errors.append("cursor: generators_run must be true")
    if not payload.get("method"):
        errors.append("cursor: method is missing")
    if not payload.get("prompt"):
        errors.append("cursor: prompt is missing")
    artefacts = payload.get("candidate_artefacts") or {}
    if artefacts.get("produced") is not False:
        errors.append("cursor: candidate_artefacts.produced must be false")
    oracle = payload.get("oracle")
    if not isinstance(oracle, dict):
        errors.append("cursor: oracle object is missing")
        return errors
    if oracle.get("stdout") != EXPECTED_ORACLE:
        errors.append("cursor: oracle.stdout must be the exact replay-only OK line")
    if oracle.get("exit") != 0:
        errors.append("cursor: oracle.exit must be 0")
    if oracle.get("match_count") != 27:
        errors.append("cursor: match_count must be 27")
    if oracle.get("mismatch_count") != 0:
        errors.append("cursor: mismatch_count must be 0")
    if payload.get("zero_mismatch_means") != "oracle too thin to discriminate":
        errors.append("cursor: zero-mismatch reading must say the oracle is too thin to discriminate")
    receipt_path = ARMS_DIR / "cursor" / "oracle-receipt.json"
    if not receipt_path.is_file():
        errors.append("cursor: missing oracle-receipt.json")
    else:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("stdout") != EXPECTED_ORACLE:
            errors.append("cursor receipt stdout must be the exact replay-only OK line")
        if receipt.get("match_count") != 27 or receipt.get("mismatch_count") != 0:
            errors.append("cursor receipt must record 27 matches and 0 mismatches")
        if receipt.get("mutation_score") != "not-stored":
            errors.append("cursor receipt must not store a mutation score")
    return errors


def check_external_slot(name: str, payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("status") != "awaiting-external-run":
        errors.append(f"{name}: status must be awaiting-external-run")
    if payload.get("generators_run") is not False:
        errors.append(f"{name}: generators_run must be false")
    if not payload.get("reason"):
        errors.append(f"{name}: reason for awaiting-external-run is missing")
    if not payload.get("prompt"):
        errors.append(f"{name}: paste-ready prompt is missing")
    prompt_path = ARMS_DIR / name / "PROMPT.md"
    if not prompt_path.is_file():
        errors.append(f"{name}: missing PROMPT.md")
    else:
        prompt_text = prompt_path.read_text(encoding="utf-8")
        if payload.get("prompt") != prompt_text:
            errors.append(f"{name}: arm.json prompt must match PROMPT.md")
        for phrase in (
            EXPECTED_ORACLE,
            "27 recorded traces",
            "too thin to discriminate",
            "paper_s1=unexecuted",
            "mutation_score=not-stored",
            "run-arm-oracle.py",
        ):
            if phrase not in prompt_text:
                errors.append(f"{name}: PROMPT.md missing {phrase!r}")
    if payload.get("script") != "subjects/django-accounting/evidence/arms/run-arm-oracle.py":
        errors.append(f"{name}: script must point at run-arm-oracle.py")
    errors.extend(f"{name}: {error}" for error in _has_invented_result(payload))
    return errors


def check_english() -> list[str]:
    if not EVIDENCE.is_file():
        return [f"missing {EVIDENCE}"]
    text = EVIDENCE.read_text(encoding="utf-8")
    errors: list[str] = []
    for phrase in (
        "paper_s1=unexecuted",
        "oracle=replay-only",
        "cases=27",
        PIN,
        "import_only_stub=true",
        "mutation_score=not-stored",
        "domain_correctness=out_of_scope",
        "codex_arm=omitted",
        "replay-only",
        "27 recorded traces",
        "domain correctness is out of scope",
        "too thin to discriminate",
        "four clean generators",
        "success theatre",
        "Cursor",
        "Claude Code",
        "Gemini",
        "awaiting-external-run",
        "Match count 27",
        "Mismatch count 0",
    ):
        if phrase not in text:
            errors.append(f"EVIDENCE.md missing {phrase!r}")
    if "four clean generators succeeded" in text.lower():
        errors.append("EVIDENCE.md must not claim four clean generators succeeded")
    return errors


def run_oracle() -> tuple[int, str, str]:
    completed = subprocess.run(
        [sys.executable, str(ORACLE)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def main() -> int:
    payload = load_posture()
    errors = check_honesty(payload) + check_arm_slots() + check_english()
    if errors:
        print("S1 PART B FAIL-CLOSED: posture check failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 2
    code, stdout, stderr = run_oracle()
    observed = stdout.rstrip("\n")
    if code != 0 or observed != EXPECTED_ORACLE:
        print("S1 PART B FAIL-CLOSED: oracle stdout was not the required replay-only OK line", file=sys.stderr)
        print(f"  expected: {EXPECTED_ORACLE}", file=sys.stderr)
        print(f"  got: {observed}", file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr, end="")
        return 2
    print(EXPECTED_ORACLE)
    print(
        "S1 PART B POSTURE OK "
        "paper_s1=unexecuted "
        "oracle=replay-only "
        f"cases=27 pin={PIN} "
        "import_only_stub=true "
        "mutation_score=not-stored "
        "domain_correctness=out_of_scope "
        "arms=3 "
        "codex_arm=omitted "
        "cursor=executed "
        "claude_code=awaiting-external-run "
        "gemini=awaiting-external-run "
        "generators_run=cursor-only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
