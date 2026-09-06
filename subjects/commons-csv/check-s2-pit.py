#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""S2 live PIT honesty gate (score-free).

Checks the committed evidence pack and, when a live work tree is
present or --require-live is set, classifies that tree without
storing a mutation score.

Fail-closed:
- numeric mutation_score / kill-rate
- missing pin gate
- --require-live with no successful live work tree
- tracked HTML report or mutations.xml / SCORE

A skip is not a pass. This is not paper S2.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SUBJECT = Path(__file__).resolve().parent
REPO = SUBJECT.parent.parent
PIN_GATE = SUBJECT / "check-pins.py"
RUNNER = SUBJECT / "run-pit.sh"
RECORDER = SUBJECT / "record-pit-receipt.py"
POSTURE = SUBJECT / "evidence" / "s2-posture.json"
RECEIPT = SUBJECT / "evidence" / "pit-receipt.json"
ENGLISH = SUBJECT / "evidence" / "EVIDENCE.md"
WORK = SUBJECT / "work"
HTML = WORK / "pit-reports" / "index.html"

if str(SUBJECT) not in sys.path:
    sys.path.insert(0, str(SUBJECT))

from toolchain import (  # noqa: E402
    classify_live_work,
    contains_forbidden_score_text,
    load_pins,
    receipt_score_errors,
)

PIN_OK_PREFIX = "S2 PIN OK"
EXPECTED_OK = (
    "S2 PIT EVIDENCE OK "
    "mutation_score=not-stored "
    "paper_s2=unexecuted"
)


def fail(message: str, extra: str = "") -> int:
    print(f"S2 FAIL-CLOSED: {message}", file=sys.stderr)
    if extra:
        print(extra, file=sys.stderr, end="" if extra.endswith("\n") else "\n")
    return 2


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)


def tracked_score_artifacts() -> list[str]:
    listed = run(["git", "ls-files", "subjects/commons-csv"])
    errors: list[str] = []
    for line in listed.stdout.splitlines():
        name = Path(line).name
        if name in {"SCORE", "mutations.xml", "mutation-score"}:
            errors.append(f"tracked mutation-score artifact: {line}")
        if line.endswith("work/pit-reports/index.html"):
            errors.append(f"PIT HTML must not be a git object: {line}")
    return errors


def check_english(status: str) -> list[str]:
    errors: list[str] = []
    if not ENGLISH.is_file():
        return [f"missing {ENGLISH}"]
    text = ENGLISH.read_text(encoding="utf-8")
    for needle in (
        "mutation_score=not-stored",
        "paper_s2=unexecuted",
        f"status={status}",
        "not a paper execution of S2",
    ):
        if needle not in text:
            errors.append(f"EVIDENCE.md missing {needle!r}")
    if contains_forbidden_score_text(text):
        errors.append("EVIDENCE.md stores a mutation-score claim")
    return errors


def check_committed_pack() -> tuple[list[str], dict, dict]:
    errors: list[str] = []
    if not POSTURE.is_file():
        return [f"missing {POSTURE}"], {}, {}
    if not RECEIPT.is_file():
        return [f"missing {RECEIPT}"], {}, {}
    posture = json.loads(POSTURE.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    pins = load_pins()

    required_posture = {
        "paper_s2": "unexecuted",
        "mutation_score": "not-stored",
    }
    for key, expected in required_posture.items():
        if posture.get(key) != expected:
            errors.append(f"posture.{key}: expected {expected!r} got {posture.get(key)!r}")
        if receipt.get(key) != expected:
            errors.append(f"receipt.{key}: expected {expected!r} got {receipt.get(key)!r}")

    status = posture.get("status")
    if status not in {"live-pit-executed"} and not (
        isinstance(status, str) and status.startswith("blocked=")
    ):
        errors.append(
            f"posture.status must be live-pit-executed or blocked=...; got {status!r}"
        )
    if posture.get("status") != receipt.get("status"):
        errors.append(
            f"posture.status {posture.get('status')!r} != receipt.status {receipt.get('status')!r}"
        )
    if status == "live-pit-executed":
        if receipt.get("executed") is not True:
            errors.append("receipt.executed must be true when status=live-pit-executed")
        if receipt.get("blocked") is not None:
            errors.append("receipt.blocked must be null when status=live-pit-executed")
        if posture.get("runner", {}).get("executed_in_this_pack") is not True:
            errors.append("posture.runner.executed_in_this_pack must be true for a live pack")
    elif isinstance(status, str) and status.startswith("blocked="):
        if receipt.get("executed") is not False:
            errors.append("receipt.executed must be false when status is blocked=")
        token = status.split("=", 1)[1]
        if not token:
            errors.append("blocked= token is empty")
        if receipt.get("blocked") != token:
            errors.append(
                f"receipt.blocked {receipt.get('blocked')!r} != posture status token {token!r}"
            )

    recorded = posture.get("pins", {})
    if recorded.get("defects4j", {}).get("commit") != pins["defects4j"]["commit"]:
        errors.append("posture defects4j commit does not match pins.toml")
    if recorded.get("commons_csv", {}).get("commit") != pins["commons_csv"]["commit"]:
        errors.append("posture commons-csv commit does not match pins.toml")
    if recorded.get("pit", {}).get("mutators") != "DEFAULTS":
        errors.append("posture pit.mutators must be DEFAULTS")
    if recorded.get("jdk", {}).get("sha256") != pins["jdk"]["sha256"]:
        errors.append("posture jdk sha256 does not match pins.toml")

    if posture.get("runner", {}).get("records_mutation_score") is not False:
        errors.append("posture.runner.records_mutation_score must be false")
    if receipt.get("records_mutation_score") is not False:
        errors.append("receipt.records_mutation_score must be false")
    if receipt.get("html_report_body_stored") is not False:
        errors.append("receipt must not store the HTML body")
    if receipt.get("pit_log_body_stored") is not False:
        errors.append("receipt must not store pit.log")
    if receipt.get("html_report_tracked") is True:
        errors.append("receipt.html_report_tracked must not be true")

    errors.extend(receipt_score_errors(posture, "posture"))
    errors.extend(receipt_score_errors(receipt, "receipt"))
    errors.extend(check_english(str(status)))
    errors.extend(tracked_score_artifacts())
    dumped = json.dumps({"posture": posture, "receipt": receipt})
    if contains_forbidden_score_text(dumped):
        errors.append("committed pack serialisation stores a mutation-score claim")
    return errors, posture, receipt


def check_live(require_live: bool, expected_status: str) -> list[str]:
    errors: list[str] = []
    executed, blocked, judge_errors = classify_live_work(WORK)
    live_present = (WORK / "pit.log").is_file() or HTML.is_file()
    if require_live:
        if not live_present:
            return ["--require-live: work/ has no pit.log or HTML report (blocked=pit-not-run)"]
        if not executed:
            detail = "; ".join(judge_errors) if judge_errors else f"blocked={blocked}"
            return [f"--require-live: live work is not a successful PIT run ({detail})"]
        if not HTML.is_file():
            return ["--require-live: live HTML report is missing"]
        return []
    if not live_present:
        return []

    if expected_status == "live-pit-executed" and not executed:
        errors.append(f"live work is not a successful PIT run (blocked={blocked})")
        errors.extend(f"judge: {item}" for item in judge_errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="S2 live PIT honesty gate")
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="fail closed if work/ is not a live fail-closed PIT tree",
    )
    args = parser.parse_args()

    if not PIN_GATE.is_file():
        return fail("check-pins.py is missing. Skip is not a pass.")
    if not RUNNER.is_file() or not RUNNER.stat().st_mode & 0o111:
        return fail("run-pit.sh is missing or not executable. Skip is not a pass.")
    if not RECORDER.is_file():
        return fail(f"missing {RECORDER}")

    pins = run([sys.executable, str(PIN_GATE)])
    if pins.returncode != 0 or not pins.stdout.startswith(PIN_OK_PREFIX):
        return fail("pin check failed", extra=pins.stderr + pins.stdout)

    errors, posture, _receipt = check_committed_pack()
    status = str(posture.get("status", ""))
    errors.extend(check_live(args.require_live, status))

    if errors:
        print("S2 FAIL-CLOSED: live PIT evidence gate failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 2

    print(pins.stdout.rstrip("\n"))
    executed = posture.get("runner", {}).get("executed_in_this_pack")
    blocked = posture.get("blocked")
    extra = f" blocked={blocked}" if blocked else ""
    print(
        f"{EXPECTED_OK} "
        f"status={status} "
        f"executed_in_this_pack={str(executed).lower()}"
        f"{extra}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
