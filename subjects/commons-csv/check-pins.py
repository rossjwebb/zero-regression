#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify S2 pin files against pins.toml. Exit non-zero on mismatch.

This is not a mutation run and does not print a mutation score.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import tomllib
from pathlib import Path

SUBJECT = Path(__file__).resolve().parent
PINS = SUBJECT / "pins.toml"
PIN = SUBJECT / "PIN"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_pins() -> dict:
    if not PINS.is_file():
        raise SystemExit(f"S2 FAIL-CLOSED: missing {PINS}")
    with PINS.open("rb") as handle:
        return tomllib.load(handle)


def check_pin_text(pins: dict) -> list[str]:
    errors: list[str] = []
    if not PIN.is_file():
        return [f"missing {PIN}"]
    text = PIN.read_text(encoding="utf-8")
    expected = {
        "defects4j_commit": pins["defects4j"]["commit"],
        "defects4j_tag": pins["defects4j"]["tag"],
        "commons_csv_commit": pins["commons_csv"]["commit"],
        "modified_class": pins["defects4j"]["modified_class"],
        "pit_version": pins["pit"]["version"],
        "pit_mutators": pins["pit"]["mutators"],
        "subject_release": str(pins["pit"]["subject_release"]),
        "pit_jdk": pins["jdk"]["release"],
    }
    for key, value in expected.items():
        line = f"{key}={value}"
        if line not in text:
            errors.append(f"PIN missing {line}")
    return errors


def check_files(pins: dict) -> list[str]:
    errors: list[str] = []
    for entry in pins["file"]:
        path = SUBJECT / entry["path"]
        expected = entry["sha256"]
        if not path.is_file():
            errors.append(f"missing {entry['path']}")
            continue
        observed = sha256_file(path)
        if observed != expected:
            errors.append(f"hash mismatch {entry['path']}: expected {expected} observed {observed}")
    return errors


def check_defects4j_row(pins: dict) -> list[str]:
    row_path = SUBJECT / "pins" / "defects4j-v3.0.1-Csv-1.active-bugs.row.csv"
    if not row_path.is_file():
        return [f"missing {row_path.name}"]
    lines = row_path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        return ["Defects4J Csv-1 row file is too short"]
    fields = lines[1].split(",")
    d4j = pins["defects4j"]
    expected = [
        d4j["bug_id"],
        d4j["buggy_commit"],
        d4j["fixed_commit"],
        d4j["report_id"],
        d4j["report_url"],
    ]
    if fields != expected:
        return [f"Defects4J Csv-1 row mismatch: {fields!r} != {expected!r}"]
    modified = (SUBJECT / "pins" / "defects4j-v3.0.1-Csv-1.modified_classes").read_text(encoding="utf-8").strip()
    if modified != d4j["modified_class"]:
        return [f"modified class mismatch: {modified!r} != {d4j['modified_class']!r}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Commons-CSV / Defects4J / PIT pins")
    parser.parse_args()
    pins = load_pins()
    errors = check_pin_text(pins) + check_files(pins) + check_defects4j_row(pins)
    if pins["pit"]["mutators"] != "DEFAULTS":
        errors.append("pit.mutators must be the named DEFAULTS group")
    if pins["pit"]["subject_release"] != 8:
        errors.append("pit.subject_release must be 8")
    if not pins["jdk"]["url"] or not pins["jdk"]["sha256"]:
        errors.append("jdk url/sha256 must be pinned from the fetched tarball")
    if errors:
        print("S2 FAIL-CLOSED: pin check failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 2
    file_count = len(pins["file"])
    jar_count = len(pins["jar"])
    print(
        "S2 PIN OK "
        f"defects4j={pins['defects4j']['tag']}@{pins['defects4j']['commit'][:12]} "
        f"csv={pins['commons_csv']['commit'][:12]} "
        f"pit={pins['pit']['version']} "
        f"mutators={pins['pit']['mutators']} "
        f"jdk={pins['jdk']['release']} "
        f"release={pins['pit']['subject_release']} "
        f"files={file_count} jars={jar_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
