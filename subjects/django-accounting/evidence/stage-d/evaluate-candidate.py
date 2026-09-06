#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evaluate one Stage D candidate against the Stage C yardstick.

Installs the candidate via the import hook (no legacy/ edit), then
replays the 27-trace oracle and the golden-independent invariants.

Prints a JSON receipt to stdout. Does not invent a mutation score.
This is not paper S1.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

STAGE_D = Path(__file__).resolve().parent
SUBJECT = STAGE_D.parents[1]
REPO = SUBJECT.parent.parent
ORACLE = SUBJECT / "oracle.py"
GOLDEN = SUBJECT / "golden" / "expected.json"
DISCRIMINATION = SUBJECT / "discrimination"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
EXPECTED_ORACLE = f"ORACLE OK pin={PIN} cases=27 replay-only"


def load_oracle():
    spec = importlib.util.spec_from_file_location("django_accounting_oracle", ORACLE)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {ORACLE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mismatched_cases(payload: dict, expected: dict) -> list[str]:
    got = payload.get("cases", {})
    exp = expected.get("cases", {})
    names = []
    for name in sorted(set(got) | set(exp)):
        if got.get(name) != exp.get(name):
            names.append(name)
    return names


def python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a Stage D candidate against Stage C")
    parser.add_argument("--candidate", required=True, help="candidate directory name under arms/<arm>/candidates/")
    parser.add_argument(
        "--arm",
        default="cursor",
        choices=("cursor", "claude-code", "gemini"),
        help="which Stage D arm candidate tree to load (default: cursor)",
    )
    args = parser.parse_args()

    if str(STAGE_D) not in sys.path:
        sys.path.insert(0, str(STAGE_D))
    if str(DISCRIMINATION) not in sys.path:
        sys.path.insert(0, str(DISCRIMINATION))

    from apply import candidates_dir, install_candidate

    manifest = install_candidate(args.candidate, arm=args.arm)
    CANDIDATES = candidates_dir(args.arm)
    oracle = load_oracle()
    payload = oracle.run_cases()
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    mismatches = mismatched_cases(payload, expected)
    match_count = len(expected.get("cases", {})) - len(mismatches)

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    saved_argv = sys.argv
    sys.argv = [str(ORACLE)]
    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            oracle_exit = oracle.main()
    finally:
        sys.argv = saved_argv

    def relativize(text: str) -> str:
        return text.replace(str(REPO) + "/", "").replace(str(REPO), ".")

    oracle_stdout = relativize(stdout_buf.getvalue())
    oracle_stderr = relativize(stderr_buf.getvalue())

    import invariants

    invariant_failures = invariants.check_live_invariants()
    oracle_ok = oracle_exit == 0 and oracle_stdout.rstrip("\n") == EXPECTED_ORACLE
    invariants_ok = not invariant_failures
    accepted = oracle_ok and invariants_ok
    reasons: list[str] = []
    if mismatches:
        reasons.append("oracle mismatch: " + ", ".join(mismatches))
    elif not oracle_ok:
        reasons.append(f"oracle exit={oracle_exit} stdout={oracle_stdout.rstrip()!r}")
    if invariant_failures:
        reasons.extend(invariant_failures)

    receipt = {
        "kind": "s1-django-accounting-stage-d-candidate-receipt",
        "arm": args.arm,
        "candidate": manifest["name"],
        "intent": manifest["intent"],
        "slice": manifest["slice"],
        "produced": True,
        "path": str((CANDIDATES / manifest["name"] / manifest["source"]).relative_to(REPO)),
        "manifest": str((CANDIDATES / manifest["name"] / "manifest.json").relative_to(REPO)),
        "legacy_edited": False,
        "golden_widened": False,
        "paper_s1": "unexecuted",
        "mutation_score": "not-stored",
        "discrimination_gate": "required",
        "domain_correctness": "out_of_scope",
        "pin": PIN,
        "python": python_version(),
        "oracle": {
            "command": (
                "python3.12 subjects/django-accounting/evidence/stage-d/"
                f"evaluate-candidate.py --arm {args.arm} --candidate {manifest['name']}"
            ),
            "python": python_version(),
            "exit": oracle_exit,
            "stdout": oracle_stdout.rstrip("\n"),
            "stderr": oracle_stderr,
            "match_count": match_count,
            "mismatch_count": len(mismatches),
            "mismatched_cases": mismatches,
            "replay_ok_line": EXPECTED_ORACLE,
            "replay_ok": oracle_ok,
        },
        "invariants": {
            "failures": invariant_failures,
            "failed": bool(invariant_failures),
            "count": 3,
        },
        "gate": {
            "yardstick": "subjects/django-accounting/check-discrimination.py",
            "verdict": "accepted" if accepted else "rejected",
            "reasons": reasons,
            "meaning": (
                "Stage C replay + golden-independent invariants applied to a "
                "produced rewrite. Not a mutation score. Not paper S1."
            ),
        },
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
