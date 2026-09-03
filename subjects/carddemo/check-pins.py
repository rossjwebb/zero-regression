#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify S3 CardDemo pin files against pins.toml. Exit non-zero on mismatch.

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
        raise SystemExit(f"S3 FAIL-CLOSED: missing {PINS}")
    with PINS.open("rb") as handle:
        return tomllib.load(handle)


def check_pin_text(pins: dict) -> list[str]:
    errors: list[str] = []
    if not PIN.is_file():
        return [f"missing {PIN}"]
    text = PIN.read_text(encoding="utf-8")
    expected = {
        "carddemo_commit": pins["carddemo"]["commit"],
        "carddemo_upstream": pins["carddemo"]["upstream"],
        "carddemo_legacy_tests": pins["carddemo"]["legacy_tests"],
        "slice_job": pins["slice"]["job"],
        "slice_program": pins["slice"]["program"],
        "compiler_gnucobol_cobc": pins["gnucobol"]["release"],
        "compiler_gnucobol_package": f"{pins['gnucobol']['package']}={pins['gnucobol']['version']}",
        "compiler_gnucobol_url": pins["gnucobol"]["url"],
        "compiler_gnucobol_sha256": pins["gnucobol"]["sha256"],
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


def check_no_legacy_tests(pins: dict) -> list[str]:
    errors: list[str] = []
    if (SUBJECT / "legacy").exists():
        errors.append("legacy/ must not exist; S3 documents that CardDemo has no legacy tests")
    if (SUBJECT / "golden").exists():
        errors.append("golden/ must not exist; S3 has no golden-file oracle")
    if pins["carddemo"]["legacy_tests"] != "none":
        errors.append(f"legacy_tests must be none, got {pins['carddemo']['legacy_tests']!r}")
    scan = SUBJECT / "pins" / "no-legacy-tests.scan.txt"
    if not scan.is_file():
        return errors + ["missing pins/no-legacy-tests.scan.txt"]
    text = scan.read_text(encoding="utf-8")
    if "legacy_tests=none" not in text:
        errors.append("scan file does not record legacy_tests=none")
    if f"commit={pins['carddemo']['commit']}" not in text:
        errors.append("scan file commit does not match the pin")
    tree = SUBJECT / "pins" / "carddemo-59cc6c2f.ls-tree.txt"
    if tree.is_file():
        names = tree.read_text(encoding="utf-8").splitlines()
        if len(names) != pins["carddemo"]["file_count"]:
            errors.append(f"ls-tree file_count {len(names)} != {pins['carddemo']['file_count']}")
        if any(name == "tests" or name.startswith("tests/") or "/test/" in name.lower() for name in names):
            errors.append("ls-tree unexpectedly contains a tests/ path")
    return errors


def check_gnucobol_pin(pins: dict) -> list[str]:
    errors: list[str] = []
    if "gnucobol" not in pins:
        return ["missing [gnucobol] pin"]
    cfg = pins["gnucobol"]
    required = {
        "package": "gnucobol3",
        "version": "3.1.2-5.1ubuntu1",
        "release": "3.1.2.0",
        "version_marker": "3.1.2.0",
        "binary": "/usr/bin/cobc",
    }
    for key, value in required.items():
        if cfg.get(key) != value:
            errors.append(f"gnucobol.{key} must be {value!r}, got {cfg.get(key)!r}")
    if not cfg.get("url", "").startswith("http://archive.ubuntu.com/ubuntu/pool/universe/g/gnucobol3/"):
        errors.append("gnucobol.url must be the Ubuntu pool fetch for gnucobol3")
    sha = cfg.get("sha256", "")
    cobc_sha = cfg.get("cobc_sha256", "")
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        errors.append("gnucobol.sha256 is not a lowercase SHA-256")
    if len(cobc_sha) != 64 or any(ch not in "0123456789abcdef" for ch in cobc_sha):
        errors.append("gnucobol.cobc_sha256 is not a lowercase SHA-256")
    debs = pins.get("deb", [])
    names = {entry.get("package") for entry in debs}
    if names != {"gnucobol3", "libcob4-dev", "libcob4t64"}:
        errors.append(f"[[deb]] packages must be gnucobol3, libcob4-dev, libcob4t64; got {sorted(names)}")
    for entry in debs:
        if entry.get("sha256") == "" or len(entry.get("sha256", "")) != 64:
            errors.append(f"[[deb]] {entry.get('package')} is missing sha256")
        if entry.get("package") == "gnucobol3" and entry.get("sha256") != sha:
            errors.append("gnucobol3 [[deb]] sha256 must match [gnucobol].sha256")
    return errors


def write_hashes(pins: dict) -> None:
    raw = PINS.read_text(encoding="utf-8")
    for entry in pins["file"]:
        path = SUBJECT / entry["path"]
        if not path.is_file():
            raise SystemExit(f"S3 FAIL-CLOSED: cannot --write, missing {entry['path']}")
        observed = sha256_file(path)
        old = f'sha256 = "{entry["sha256"]}"'
        # Replace only the hash that sits under this path block.
        marker = f'path = "{entry["path"]}"\nsha256 = "{entry["sha256"]}"'
        replacement = f'path = "{entry["path"]}"\nsha256 = "{observed}"'
        if marker not in raw:
            if old in raw and entry["sha256"] != observed:
                raise SystemExit(f"S3 FAIL-CLOSED: ambiguous hash replace for {entry['path']}")
            continue
        raw = raw.replace(marker, replacement, 1)
    PINS.write_text(raw, encoding="utf-8")
    print(f"wrote hashes into {PINS}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify CardDemo pins")
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite [[file]] hashes from the working tree (deliberate pin change only)",
    )
    args = parser.parse_args()
    pins = load_pins()
    if args.write:
        write_hashes(pins)
        pins = load_pins()
    errors = check_pin_text(pins) + check_files(pins) + check_no_legacy_tests(pins) + check_gnucobol_pin(pins)
    if errors:
        print("S3 FAIL-CLOSED: pin check failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 2
    file_count = len(pins["file"])
    print(
        "S3 PIN OK "
        f"carddemo={pins['carddemo']['commit'][:12]} "
        f"slice={pins['slice']['job']}/{pins['slice']['program']} "
        f"legacy_tests={pins['carddemo']['legacy_tests']} "
        f"files={file_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
