#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""S1 Part B honesty gate for django-accounting.

Requires the existing replay-only oracle stdout exactly. Checks the
Part B posture pack. Does not run a generator and does not record a
mutation score. This is not paper S1.
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
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_ORACLE = f"ORACLE OK pin={PIN} cases=27 replay-only"
ARM_KEYS = ("cursor", "claude_code", "gemini")
ARM_DIRS = ("cursor", "claude-code", "gemini")


def fail(message: str) -> int:
    print(f"S1 PART B FAIL-CLOSED: {message}", file=sys.stderr)
    return 2


def load_posture() -> dict:
    if not POSTURE.is_file():
        raise SystemExit(fail(f"missing {POSTURE}"))
    return json.loads(POSTURE.read_text(encoding="utf-8"))


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
    if isinstance(payload.get("mutation_score"), (int, float)):
        errors.append("mutation_score must not be numeric")
    claims = payload.get("claims")
    if not isinstance(claims, dict):
        errors.append("claims object is missing")
        return errors
    for key, expected in required.items():
        if claims.get(key) != expected:
            errors.append(f"claims.{key}: expected {expected!r} got {claims.get(key)!r}")
    if claims.get("generators_run") is not False:
        errors.append("claims.generators_run must be false")
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
        for key in ARM_KEYS:
            if generators.get(key) is not False:
                errors.append(f"generators_run.{key} must be false")
    arms = payload.get("arms")
    if not isinstance(arms, dict):
        errors.append("arms object is missing")
    else:
        if set(arms) != set(ARM_KEYS):
            errors.append(f"arms keys must be {ARM_KEYS}, got {tuple(arms)}")
        if "codex" in arms or "codex_arm" in arms:
            errors.append("Codex must not appear as an arm")
        for key in ARM_KEYS:
            arm = arms.get(key) or {}
            if arm.get("status") != "not-run":
                errors.append(f"arms.{key}.status must be not-run")
            if arm.get("generators_run") is not False:
                errors.append(f"arms.{key}.generators_run must be false")
    if not payload.get("codex_omission_reason"):
        errors.append("codex_omission_reason is missing")
    oracle_gate = payload.get("oracle_gate") or {}
    if oracle_gate.get("stdout") != EXPECTED_ORACLE:
        errors.append("oracle_gate.stdout must be the exact replay-only OK line")
    return errors


def check_arm_slots() -> list[str]:
    errors: list[str] = []
    if (ARMS_DIR / "codex").exists():
        errors.append("Codex arm directory must not exist")
    for name in ARM_DIRS:
        path = ARMS_DIR / name / "arm.json"
        if not path.is_file():
            errors.append(f"missing arm slot {path}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "not-run":
            errors.append(f"{name}: status must be not-run")
        if payload.get("generators_run") is not False:
            errors.append(f"{name}: generators_run must be false")
        if "mutation_score" in payload and isinstance(payload["mutation_score"], (int, float)):
            errors.append(f"{name}: mutation_score must not be numeric")
        if "kill_rate" in payload and isinstance(payload["kill_rate"], (int, float)):
            errors.append(f"{name}: kill_rate must not be numeric")
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
    ):
        if phrase not in text:
            errors.append(f"EVIDENCE.md missing {phrase!r}")
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
        "generators_run=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
