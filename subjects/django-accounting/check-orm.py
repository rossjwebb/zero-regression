#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""S1 ORM honesty gate.

Requires the 27-trace replay oracle still green, the Django 5.2.17 pin
lock consistent, and a live org-aggregates run that issued SUM SQL
through the pin's QuerySet classes.

This is not paper S1. It stores no mutation score. A missing Django
install is fail-closed (blocked=django-not-installed), not a pass.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SUBJECT = Path(__file__).resolve().parent
REPO = SUBJECT.parent.parent
ORACLE = SUBJECT / "oracle.py"
WRITE_LOCK = SUBJECT / "orm" / "write-lock.py"
RUNNER = SUBJECT / "orm" / "run-org-aggregates.py"
POSTURE = SUBJECT / "evidence" / "orm" / "posture.json"
ENGLISH = SUBJECT / "evidence" / "orm" / "EVIDENCE.md"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_ORACLE = f"ORACLE OK pin={PIN} cases=27 replay-only"
EXPECTED_ORM = (
    f"S1 ORM OK pin={PIN} django=5.2.17 "
    "path=pin-managers-queryset-aggregate "
    "paper_s1=unexecuted mutation_score=not-stored"
)


def fail(message: str, extra: str = "") -> int:
    print(f"S1 ORM FAIL-CLOSED: {message}", file=sys.stderr)
    if extra:
        print(extra, file=sys.stderr, end="" if extra.endswith("\n") else "\n")
    return 2


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)


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


def check_posture() -> list[str]:
    errors: list[str] = []
    if not POSTURE.is_file():
        return [f"missing {POSTURE}"]
    payload = json.loads(POSTURE.read_text(encoding="utf-8"))
    required = {
        "paper_s1": "unexecuted",
        "mutation_score": "not-stored",
        "orm_sql_executed": True,
        "path": "pin-managers-queryset-aggregate",
        "pin": PIN,
        "django": "5.2.17",
        "pin_models_imported": False,
        "legacy_edited": False,
        "golden_widened": False,
        "domain_correctness": "out_of_scope",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            errors.append(f"posture.{key}: expected {expected!r} got {payload.get(key)!r}")
    if "kill_rate" in payload:
        errors.append("posture must not store kill_rate")
    errors.extend(check_score_free(payload))
    if not ENGLISH.is_file():
        errors.append(f"missing {ENGLISH}")
    else:
        text = ENGLISH.read_text(encoding="utf-8")
        for needle in (
            "paper_s1=unexecuted",
            "mutation_score=not-stored",
            "pin-managers-queryset-aggregate",
            "not paper S1",
        ):
            if needle not in text:
                errors.append(f"EVIDENCE.md missing {needle!r}")
        if "killed/seeded" in text.lower():
            errors.append("EVIDENCE.md must not state a killed/seeded score")
    return errors


def main() -> int:
    if not ORACLE.is_file():
        return fail("oracle.py is missing. Skip is not a pass.")
    if not RUNNER.is_file():
        return fail(f"missing {RUNNER}")
    if not WRITE_LOCK.is_file():
        return fail(f"missing {WRITE_LOCK}")

    errors: list[str] = []
    errors.extend(check_posture())

    lock = run([sys.executable, str(WRITE_LOCK), "--check"])
    if lock.returncode != 0:
        return fail("Django lock/pin mismatch", extra=lock.stderr + lock.stdout)

    good = run([sys.executable, str(ORACLE)])
    observed = good.stdout.rstrip("\n")
    if good.returncode != 0 or observed != EXPECTED_ORACLE:
        return fail(
            "good pin did not print the required replay-only OK line",
            extra=f"  expected: {EXPECTED_ORACLE}\n  got: {observed}\n{good.stderr}",
        )

    orm = run([sys.executable, str(RUNNER)])
    if orm.returncode != 0:
        return fail(
            "org-aggregates runner failed (Django missing is blocked=, not a pass)",
            extra=orm.stderr + orm.stdout,
        )
    lines = [line for line in orm.stdout.splitlines() if line.strip()]
    if not lines or lines[0] != EXPECTED_ORM:
        return fail(
            "org-aggregates runner did not print the required ORM OK line",
            extra=f"  expected: {EXPECTED_ORM}\n  got: {orm.stdout!r}\n{orm.stderr}",
        )
    try:
        receipt = json.loads("\n".join(lines[1:]))
    except json.JSONDecodeError as exc:
        return fail(f"org-aggregates receipt is not JSON: {exc}", extra=orm.stdout)
    if receipt.get("orm_sql_executed") is not True:
        errors.append("receipt.orm_sql_executed must be true")
    if receipt.get("paper_s1") != "unexecuted":
        errors.append("receipt.paper_s1 must be unexecuted")
    if receipt.get("mutation_score") != "not-stored":
        errors.append("receipt.mutation_score must be not-stored")
    if receipt.get("pin_models_imported") is not False:
        errors.append("receipt must not claim pin models.py imported")
    if not receipt.get("sql"):
        errors.append("receipt.sql must list captured SUM statements")
    errors.extend(check_score_free(receipt, "receipt"))

    if errors:
        print("S1 ORM FAIL-CLOSED: gate failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 2

    print(EXPECTED_ORACLE)
    print(EXPECTED_ORM)
    print(
        "S1 ORM POSTURE OK "
        "paper_s1=unexecuted "
        "mutation_score=not-stored "
        "path=pin-managers-queryset-aggregate "
        "orm_sql_executed=true "
        "pin_models_imported=false "
        "blocked=pin-models-django-1.7-apis"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
