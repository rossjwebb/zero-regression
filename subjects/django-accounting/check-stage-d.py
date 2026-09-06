#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""S1 Stage D honesty gate.

Requires the Stage C yardstick still green (good pin + discrimination).
Re-evaluates produced Cursor candidates against that yardstick.
Gemini may be executed with live receipts (re-evaluated via --arm gemini).
Claude Code must remain awaiting-external-run with no invented oracle
numbers until that arm actually runs.

This is not paper S1. It stores no mutation score.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SUBJECT = Path(__file__).resolve().parent
REPO = SUBJECT.parent.parent
STAGE_D = SUBJECT / "evidence" / "stage-d"
ORACLE = SUBJECT / "oracle.py"
DISCRIMINATION = SUBJECT / "check-discrimination.py"
EVALUATE = STAGE_D / "evaluate-candidate.py"
POSTURE = STAGE_D / "posture.json"
ENGLISH = STAGE_D / "EVIDENCE.md"
CURSOR_ARM = STAGE_D / "arms" / "cursor" / "arm.json"
CANDIDATES_DIR = STAGE_D / "arms" / "cursor" / "candidates"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_ORACLE = f"ORACLE OK pin={PIN} cases=27 replay-only"
REQUIRED_CANDIDATES = ("price-faithful", "price-tax-ignored", "profits-no-window")
REQUIRED_REJECTED = ("price-tax-ignored", "profits-no-window")
AWAITING_EXTERNAL_ARMS = ("claude-code",)
EXECUTABLE_EXTERNAL_ARMS = ("gemini",)
GEMINI_CANDIDATES = (
    "faithful-price-round",
    "weak-tax-truncation",
    "weak-profits-zero-override",
)
GEMINI_REQUIRED_REJECTED = ("weak-tax-truncation",)


def fail(message: str, extra: str = "") -> int:
    print(f"S1 STAGE D FAIL-CLOSED: {message}", file=sys.stderr)
    if extra:
        print(extra, file=sys.stderr, end="" if extra.endswith("\n") else "\n")
    return 2


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(fail(f"missing {path}"))
    return json.loads(path.read_text(encoding="utf-8"))


def check_score_free(node: object, prefix: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{prefix}.{key}" if prefix else key
            if key == "mutation_score":
                if isinstance(value, (int, float)):
                    errors.append(f"{here} must not be numeric")
                elif value not in ("not-stored", None):
                    errors.append(f"{here}: expected 'not-stored' got {value!r}")
            if key in {"kill_rate", "killed", "seeded", "survivors"}:
                if isinstance(value, (int, float)):
                    errors.append(f"{here} must not be numeric")
            errors.extend(check_score_free(value, here))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            errors.extend(check_score_free(item, f"{prefix}[{index}]"))
    return errors


def check_awaiting_external_slot(name: str, slot: dict) -> list[str]:
    errors: list[str] = []
    if slot.get("status") != "awaiting-external-run":
        errors.append(f"{name}.status: expected awaiting-external-run got {slot.get('status')!r}")
    if slot.get("generators_run") is not False:
        errors.append(f"{name}.generators_run must be false until that arm runs")
    artefacts = slot.get("candidate_artefacts") or {}
    if artefacts.get("produced") is not False:
        errors.append(f"{name}.candidate_artefacts.produced must be false")
    if slot.get("paper_s1") != "unexecuted":
        errors.append(f"{name}.paper_s1 must be unexecuted")
    if slot.get("mutation_score") != "not-stored":
        errors.append(f"{name}.mutation_score must be not-stored")
    if "oracle" in slot and isinstance(slot["oracle"], dict):
        observed = slot["oracle"]
        if any(key in observed for key in ("stdout", "match_count", "mismatch_count", "exit")):
            errors.append(
                f"{name} invented an oracle result while awaiting-external-run"
            )
    return errors


def check_executed_external_slot(name: str, slot: dict) -> list[str]:
    errors: list[str] = []
    if slot.get("status") != "executed":
        errors.append(f"{name}.status: expected executed got {slot.get('status')!r}")
    if slot.get("generators_run") is not True:
        errors.append(f"{name}.generators_run must be true")
    artefacts = slot.get("candidate_artefacts") or {}
    if artefacts.get("produced") is not True:
        errors.append(f"{name}.candidate_artefacts.produced must be true")
    if slot.get("paper_s1") != "unexecuted":
        errors.append(f"{name}.paper_s1 must be unexecuted")
    if slot.get("mutation_score") != "not-stored":
        errors.append(f"{name}.mutation_score must be not-stored")
    if slot.get("discrimination_gate") != "required":
        errors.append(f"{name}.discrimination_gate must be required")
    if slot.get("legacy_edited") is True:
        errors.append(f"{name}.legacy_edited must not be true")
    if slot.get("golden_widened") is True:
        errors.append(f"{name}.golden_widened must not be true")
    return errors


def check_posture(payload: dict) -> list[str]:
    errors: list[str] = []
    required = {
        "stage": "D",
        "paper_s1": "unexecuted",
        "mutation_score": "not-stored",
        "discrimination_gate": "required",
        "domain_correctness": "out_of_scope",
        "pin": PIN,
        "cases": 27,
        "produced": True,
        "golden_widened": False,
        "legacy_edited": False,
        "orm_sql_executed": False,
        "codex_arm": "omitted",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            errors.append(f"posture.{key}: expected {expected!r} got {payload.get(key)!r}")
    if isinstance(payload.get("mutation_score"), (int, float)):
        errors.append("posture.mutation_score must not be numeric")
    if "kill_rate" in payload:
        errors.append("posture must not store kill_rate")
    claims = payload.get("claims")
    if not isinstance(claims, dict):
        errors.append("posture.claims object is missing")
    else:
        for key in ("paper_s1", "mutation_score", "discrimination_gate", "stage"):
            if claims.get(key) != required[key]:
                errors.append(
                    f"posture.claims.{key}: expected {required[key]!r} got {claims.get(key)!r}"
                )
    errors.extend(check_score_free(payload, "posture"))
    return errors


def live_receipt(name: str, arm: str = "cursor") -> dict:
    command = [sys.executable, str(EVALUATE), "--arm", arm, "--candidate", name]
    result = run(command)
    if result.returncode != 0:
        raise SystemExit(
            fail(
                f"evaluate-candidate.py failed for {name}",
                extra=result.stderr or result.stdout,
            )
        )
    return json.loads(result.stdout)


def compare_receipt(name: str, stored: dict, live: dict) -> list[str]:
    errors: list[str] = []
    pairs = (
        ("gate.verdict", stored.get("gate", {}).get("verdict"), live.get("gate", {}).get("verdict")),
        ("oracle.exit", stored.get("oracle", {}).get("exit"), live.get("oracle", {}).get("exit")),
        (
            "oracle.mismatched_cases",
            stored.get("oracle", {}).get("mismatched_cases"),
            live.get("oracle", {}).get("mismatched_cases"),
        ),
        (
            "oracle.match_count",
            stored.get("oracle", {}).get("match_count"),
            live.get("oracle", {}).get("match_count"),
        ),
        (
            "oracle.mismatch_count",
            stored.get("oracle", {}).get("mismatch_count"),
            live.get("oracle", {}).get("mismatch_count"),
        ),
        (
            "invariants.failed",
            stored.get("invariants", {}).get("failed"),
            live.get("invariants", {}).get("failed"),
        ),
        ("paper_s1", stored.get("paper_s1"), live.get("paper_s1")),
        ("mutation_score", stored.get("mutation_score"), live.get("mutation_score")),
    )
    for label, left, right in pairs:
        if left != right:
            errors.append(f"{name} {label}: stored {left!r} != live {right!r}")
    return errors


def main() -> int:
    errors: list[str] = []

    if not ORACLE.is_file():
        return fail("oracle.py is missing. Skip is not a pass.")
    if not DISCRIMINATION.is_file():
        return fail("check-discrimination.py is missing.")
    if not EVALUATE.is_file():
        return fail("evaluate-candidate.py is missing.")

    good = run([sys.executable, str(ORACLE)])
    observed = good.stdout.rstrip("\n")
    if good.returncode != 0 or observed != EXPECTED_ORACLE:
        return fail(
            "good pin did not print the required replay-only OK line",
            extra=f"  expected: {EXPECTED_ORACLE}\n  got: {observed}\n{good.stderr}",
        )

    discrimination = run([sys.executable, str(DISCRIMINATION)])
    if discrimination.returncode != 0 or "DISCRIMINATION OK" not in discrimination.stdout:
        return fail(
            "Stage C discrimination gate is not green",
            extra=discrimination.stderr or discrimination.stdout,
        )

    posture = load_json(POSTURE)
    errors.extend(check_posture(posture))

    english = ENGLISH.read_text(encoding="utf-8") if ENGLISH.is_file() else ""
    if not english:
        errors.append("missing Stage D EVIDENCE.md")
    else:
        for needle in (
            "paper_s1=unexecuted",
            "mutation_score=not-stored",
            "discrimination_gate=required",
            "not paper S1",
            "rewrite",
        ):
            if needle.lower() not in english.lower() and needle not in english:
                errors.append(f"EVIDENCE.md must contain {needle!r}")
        lowered = english.lower()
        if "generators succeeded" in lowered or "paper s1 ran" in lowered:
            errors.append("EVIDENCE.md must not claim generators succeeded or paper S1 ran")

    cursor = load_json(CURSOR_ARM)
    if cursor.get("status") != "executed":
        errors.append(f"cursor.status: expected executed got {cursor.get('status')!r}")
    if cursor.get("generators_run") is not True:
        errors.append("cursor.generators_run must be true")
    artefacts = cursor.get("candidate_artefacts") or {}
    if artefacts.get("produced") is not True:
        errors.append("cursor.candidate_artefacts.produced must be true")
    if cursor.get("paper_s1") != "unexecuted":
        errors.append("cursor.paper_s1 must be unexecuted")
    if cursor.get("mutation_score") != "not-stored":
        errors.append("cursor.mutation_score must be not-stored")
    errors.extend(check_score_free(cursor, "cursor"))

    for name in AWAITING_EXTERNAL_ARMS:
        slot = load_json(STAGE_D / "arms" / name / "arm.json")
        errors.extend(check_awaiting_external_slot(name, slot))
        errors.extend(check_score_free(slot, name))
        prompt_path = STAGE_D / "arms" / name / "PROMPT.md"
        if not prompt_path.is_file():
            errors.append(f"missing {prompt_path}")
        elif slot.get("prompt") != prompt_path.read_text(encoding="utf-8"):
            errors.append(f"{name}.prompt must match PROMPT.md")

    gemini_status = "awaiting-external-run"
    gemini_accepted: list[str] = []
    gemini_rejected: list[str] = []
    for name in EXECUTABLE_EXTERNAL_ARMS:
        slot = load_json(STAGE_D / "arms" / name / "arm.json")
        prompt_path = STAGE_D / "arms" / name / "PROMPT.md"
        if not prompt_path.is_file():
            errors.append(f"missing {prompt_path}")
        elif slot.get("prompt") != prompt_path.read_text(encoding="utf-8"):
            errors.append(f"{name}.prompt must match PROMPT.md")
        errors.extend(check_score_free(slot, name))
        status = slot.get("status")
        if status == "awaiting-external-run":
            errors.extend(check_awaiting_external_slot(name, slot))
            continue
        errors.extend(check_executed_external_slot(name, slot))
        if name == "gemini":
            gemini_status = "executed"
            gemini_dir = STAGE_D / "arms" / "gemini" / "candidates"
            for cand in GEMINI_CANDIDATES:
                source = gemini_dir / cand / "manifest.json"
                if not source.is_file():
                    errors.append(f"missing gemini candidate {source}")
                    continue
                stored_path = STAGE_D / "arms" / "gemini" / "receipts" / f"{cand}.json"
                stored = load_json(stored_path)
                live = live_receipt(cand, arm="gemini")
                errors.extend(compare_receipt(f"gemini.{cand}", stored, live))
                if live.get("arm") != "gemini":
                    errors.append(f"gemini.{cand} live receipt arm must be gemini")
                verdict = live.get("gate", {}).get("verdict")
                if verdict == "rejected":
                    gemini_rejected.append(cand)
                elif verdict == "accepted":
                    gemini_accepted.append(cand)
                else:
                    errors.append(f"gemini.{cand} has no honest gate verdict")
                if stored.get("produced") is not True:
                    errors.append(f"gemini.{cand} receipt produced must be true")
            for cand in GEMINI_REQUIRED_REJECTED:
                if cand not in gemini_rejected:
                    errors.append(
                        f"gemini intentional weak {cand} must be rejected by the yardstick"
                    )
            if not gemini_rejected:
                errors.append("gemini Stage D requires at least one rejected candidate")

    rejected = []
    accepted = []
    for name in REQUIRED_CANDIDATES:
        source = CANDIDATES_DIR / name / "manifest.json"
        if not source.is_file():
            errors.append(f"missing candidate {source}")
            continue
        stored_path = STAGE_D / "arms" / "cursor" / "receipts" / f"{name}.json"
        stored = load_json(stored_path)
        live = live_receipt(name)
        errors.extend(compare_receipt(name, stored, live))
        verdict = live.get("gate", {}).get("verdict")
        if verdict == "rejected":
            rejected.append(name)
        elif verdict == "accepted":
            accepted.append(name)
        else:
            errors.append(f"{name} has no honest gate verdict")
        if stored.get("produced") is not True:
            errors.append(f"{name} receipt produced must be true")

    for name in REQUIRED_REJECTED:
        if name not in rejected:
            errors.append(f"intentional weak candidate {name} must be rejected by the yardstick")
    if not rejected:
        errors.append("Stage D requires at least one produced candidate rejected by the yardstick")

    if errors:
        print("S1 STAGE D FAIL-CLOSED: gate failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 2

    print(EXPECTED_ORACLE)
    print(
        "STAGE D OK "
        "cursor=executed "
        "produced=true "
        f"candidates={len(REQUIRED_CANDIDATES)} "
        f"accepted={len(accepted)} "
        f"rejected={len(rejected)} "
        "paper_s1=unexecuted "
        "mutation_score=not-stored "
        "discrimination_gate=required "
        "claude_code=awaiting-external-run "
        f"gemini={gemini_status} "
        f"gemini_accepted={len(gemini_accepted)} "
        f"gemini_rejected={len(gemini_rejected)} "
        "codex_arm=omitted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
