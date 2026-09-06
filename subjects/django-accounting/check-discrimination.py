#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""S1 Stage C discrimination gate.

Good pin + good stubs must print the replay-only ORACLE OK line.
Each known-bad probe must fail with a named case mismatch.
The golden-echo stub must fail the invariant gate even if replay
would have passed.

This is not paper S1. It stores no mutation score. known_bad_rejected
is a probe count, not a kill rate.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SUBJECT = Path(__file__).resolve().parent
REPO = SUBJECT.parent.parent
ORACLE = SUBJECT / "oracle.py"
DISCRIMINATION = SUBJECT / "discrimination"
RUN_ORACLE = DISCRIMINATION / "run_oracle.py"
POSTURE = SUBJECT / "evidence" / "discrimination" / "posture.json"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_ORACLE = f"ORACLE OK pin={PIN} cases=27 replay-only"
KNOWN_BAD = (
    ("bad_price_tax_zero", "price_from_tax"),
    ("bad_fully_paid", "invoice_fully_paid"),
    ("bad_profits", "profits_period_2024_jan_feb"),
    ("bad_mixed_rate_silent", "payment_allocation_mixed_rate"),
    ("bad_unknown_tax_silent", "price_unknown_tax_access"),
)
INVARIANT_COUNT = 3


def fail(message: str, extra: str = "") -> int:
    print(f"S1 DISCRIMINATION FAIL-CLOSED: {message}", file=sys.stderr)
    if extra:
        print(extra, file=sys.stderr, end="" if extra.endswith("\n") else "\n")
    return 2


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)


def load_invariants():
    if str(DISCRIMINATION) not in sys.path:
        sys.path.insert(0, str(DISCRIMINATION))
    import invariants  # noqa: PLC0415

    return invariants


def check_posture_file() -> list[str]:
    errors: list[str] = []
    if not POSTURE.is_file():
        return [f"missing {POSTURE}"]
    import json

    payload = json.loads(POSTURE.read_text(encoding="utf-8"))
    required = {
        "paper_s1": "unexecuted",
        "mutation_score": "not-stored",
        "known_bad_rejected": 5,
        "invariants": 3,
        "golden_echo_rejected": True,
        "domain_correctness": "out_of_scope",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            errors.append(f"posture.{key}: expected {expected!r} got {payload.get(key)!r}")
    if isinstance(payload.get("mutation_score"), (int, float)):
        errors.append("posture.mutation_score must not be numeric")
    if "kill_rate" in payload:
        errors.append("posture must not store kill_rate")
    return errors


def main() -> int:
    if not ORACLE.is_file():
        return fail("oracle.py is missing. Skip is not a pass.")
    if not RUN_ORACLE.is_file():
        return fail(f"missing {RUN_ORACLE}")

    errors: list[str] = []
    errors.extend(check_posture_file())

    good = run([sys.executable, str(ORACLE)])
    observed = good.stdout.rstrip("\n")
    if good.returncode != 0 or observed != EXPECTED_ORACLE:
        return fail(
            "good pin did not print the required replay-only OK line",
            extra=f"  expected: {EXPECTED_ORACLE}\n  got: {observed}\n{good.stderr}",
        )

    invariants = load_invariants()
    live_errors = invariants.check_live_invariants()
    if live_errors:
        errors.extend(live_errors)

    rejected = 0
    for name, case in KNOWN_BAD:
        result = run([sys.executable, str(RUN_ORACLE), "--probe", name])
        if result.returncode == 0:
            errors.append(
                f"known-bad probe {name} passed; the yardstick cannot discriminate"
            )
            continue
        if f"case {case}:" not in result.stderr:
            errors.append(
                f"known-bad probe {name} exited {result.returncode} but stderr "
                f"did not name case {case!r}\n{result.stderr}"
            )
            continue
        rejected += 1

    echo = run([sys.executable, str(RUN_ORACLE), "--probe", "golden_echo"])
    echo_stdout = echo.stdout.rstrip("\n")
    echo_replay_would_pass = echo.returncode == 0 and echo_stdout == EXPECTED_ORACLE
    if not echo_replay_would_pass:
        errors.append(
            "golden echo must demonstrate that a memorized golden file can "
            f"print the replay OK line; got exit={echo.returncode} stdout={echo_stdout!r}"
        )
    echo_invariant_errors = invariants.check_golden_echo_invariants()
    if not echo_invariant_errors:
        errors.append("golden echo was not rejected by the invariant gate")
    elif not any("pin not executed" in item for item in echo_invariant_errors):
        errors.append(
            "golden echo invariant rejection must say the pin was not executed; "
            f"got {echo_invariant_errors}"
        )

    if errors:
        print("S1 DISCRIMINATION FAIL-CLOSED: gate failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 2

    print(EXPECTED_ORACLE)
    print(
        "DISCRIMINATION OK "
        "good_pin=pass "
        f"known_bad_rejected={rejected} "
        "golden_echo_rejected=1 "
        f"invariants={INVARIANT_COUNT} "
        "paper_s1=unexecuted "
        "mutation_score=not-stored "
        "domain_correctness=out_of_scope"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
