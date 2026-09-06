#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Write or check the Django 5.2.17 pin from downloaded wheels.

Hashes are taken from the wheel files (and cross-checked against the
PyPI JSON sha256). They are not typed by hand. --write updates
lock.json, requirements.lock, and pins.toml. --check only compares
those three files to each other.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ORM = Path(__file__).resolve().parent
LOCK = ORM / "lock.json"
REQUIREMENTS = ORM / "requirements.lock"
PINS = ORM / "pins.toml"

PINNED = (
    {
        "name": "Django",
        "version": "5.2.17",
        "filename": "django-5.2.17-py3-none-any.whl",
        "pypi_json": "https://pypi.org/pypi/Django/5.2.17/json",
        "url": "https://files.pythonhosted.org/packages/df/f8/ce120525ca78f12b07daf65786679c5d0b54a75285a8958d3ae55e39da35/django-5.2.17-py3-none-any.whl",
        "requires_python": ">=3.10",
        "licence": "BSD-3-Clause",
    },
    {
        "name": "asgiref",
        "version": "3.12.1",
        "filename": "asgiref-3.12.1-py3-none-any.whl",
        "pypi_json": "https://pypi.org/pypi/asgiref/3.12.1/json",
        "url": "https://files.pythonhosted.org/packages/c0/1b/54f4ad77cd8a584fa70746c47df988e002cf1ee1eba43364d46f87803647/asgiref-3.12.1-py3-none-any.whl",
        "requires_python": ">=3.9",
        "licence": "BSD-3-Clause",
    },
    {
        "name": "sqlparse",
        "version": "0.6.0",
        "filename": "sqlparse-0.6.0-py3-none-any.whl",
        "pypi_json": "https://pypi.org/pypi/sqlparse/0.6.0/json",
        "url": "https://files.pythonhosted.org/packages/d9/50/f00935da0ec7cbf325f8dc4f772ae46fbc7b672dd62876e73f0a94adda57/sqlparse-0.6.0-py3-none-any.whl",
        "requires_python": ">=3.8",
        "licence": "BSD-3-Clause",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lock() -> dict:
    if not LOCK.is_file():
        raise SystemExit(f"S1 ORM FAIL-CLOSED: missing {LOCK}")
    return json.loads(LOCK.read_text(encoding="utf-8"))


def parse_requirements() -> dict[str, dict[str, str]]:
    if not REQUIREMENTS.is_file():
        raise SystemExit(f"S1 ORM FAIL-CLOSED: missing {REQUIREMENTS}")
    text = REQUIREMENTS.read_text(encoding="utf-8")
    parsed: dict[str, dict[str, str]] = {}
    for match in re.finditer(
        r"^([A-Za-z0-9_.-]+)==([0-9][^\s\\]*)\s*\\\n\s*--hash=sha256:([0-9a-f]{64})",
        text,
        flags=re.MULTILINE,
    ):
        parsed[match.group(1)] = {"version": match.group(2), "sha256": match.group(3)}
    return parsed


def parse_pins() -> dict:
    if not PINS.is_file():
        raise SystemExit(f"S1 ORM FAIL-CLOSED: missing {PINS}")
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        raise SystemExit("S1 ORM FAIL-CLOSED: tomllib is required")
    with PINS.open("rb") as handle:
        return tomllib.load(handle)


def requirements_text(wheels: list[dict]) -> str:
    lines = [
        "# Written from lock.json (wheel SHA-256). Do not type hashes by hand.",
        "# python==3.12.3",
        "# pip install --require-hashes -r subjects/django-accounting/orm/requirements.lock",
        "",
    ]
    for wheel in wheels:
        lines.append(f"{wheel['name']}=={wheel['version']} \\")
        lines.append(f"    --hash=sha256:{wheel['sha256']}")
    lines.append("")
    return "\n".join(lines)


def pins_text(lock: dict) -> str:
    django = next(item for item in lock["wheel"] if item["name"] == "Django")
    lines = [
        "# Written from lock.json by write-lock.py. Do not type hashes by hand.",
        "",
        "[subject]",
        'name = "django-accounting"',
        f'pin = "{lock["subject_pin"]}"',
        'orm_path = "pin-managers-queryset-aggregate"',
        'paper_s1 = "unexecuted"',
        'mutation_score = "not-stored"',
        "",
        "[django]",
        f'version = "{django["version"]}"',
        f'filename = "{django["filename"]}"',
        f'url = "{django["url"]}"',
        f'sha256 = "{django["sha256"]}"',
        'requires_python = ">=3.10"',
        'licence = "BSD-3-Clause"',
        'lts = "5.2"',
        'note = "Django 1.7 (the pin era) does not run on Python 3.12.3. This is the 5.2 LTS that does."',
        "",
        "[python]",
        'version = "3.12.3"',
        "",
    ]
    for wheel in lock["wheel"]:
        lines.extend(
            [
                "[[wheel]]",
                f'name = "{wheel["name"]}"',
                f'version = "{wheel["version"]}"',
                f'filename = "{wheel["filename"]}"',
                f'url = "{wheel["url"]}"',
                f'sha256 = "{wheel["sha256"]}"',
                f'licence = "{wheel["licence"]}"',
                "",
            ]
        )
    return "\n".join(lines)


def write_from_wheels(wheel_dir: Path) -> dict:
    wheels = []
    for spec in PINNED:
        path = wheel_dir / spec["filename"]
        if not path.is_file():
            raise SystemExit(f"S1 ORM FAIL-CLOSED: missing wheel {path}")
        observed = sha256_file(path)
        wheels.append(
            {
                "name": spec["name"],
                "version": spec["version"],
                "filename": spec["filename"],
                "url": spec["url"],
                "pypi_json": spec["pypi_json"],
                "sha256": observed,
                "size": path.stat().st_size,
                "requires_python": spec["requires_python"],
                "licence": spec["licence"],
            }
        )
    lock = {
        "kind": "s1-django-accounting-orm-lock",
        "written_from": "sha256 of downloaded wheels; URLs from PyPI JSON",
        "subject_pin": "2e61776a653e719a4c15578ab385603a6066c2b6",
        "python": "3.12.3",
        "paper_s1": "unexecuted",
        "mutation_score": "not-stored",
        "wheel": wheels,
    }
    LOCK.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REQUIREMENTS.write_text(requirements_text(wheels), encoding="utf-8")
    PINS.write_text(pins_text(lock), encoding="utf-8")
    return lock


def check_consistency() -> list[str]:
    errors: list[str] = []
    lock = load_lock()
    req = parse_requirements()
    pins = parse_pins()
    if lock.get("paper_s1") != "unexecuted":
        errors.append("lock.paper_s1 must be unexecuted")
    if lock.get("mutation_score") != "not-stored":
        errors.append("lock.mutation_score must be not-stored")
    if lock.get("python") != "3.12.3":
        errors.append(f"lock.python: expected 3.12.3 got {lock.get('python')!r}")
    if pins.get("django", {}).get("version") != "5.2.17":
        errors.append(f"pins.django.version: expected 5.2.17 got {pins.get('django', {}).get('version')!r}")
    if pins.get("python", {}).get("version") != "3.12.3":
        errors.append("pins.python.version must be 3.12.3")
    if pins.get("subject", {}).get("paper_s1") != "unexecuted":
        errors.append("pins.subject.paper_s1 must be unexecuted")
    if pins.get("subject", {}).get("mutation_score") != "not-stored":
        errors.append("pins.subject.mutation_score must be not-stored")
    lock_wheels = {item["name"]: item for item in lock.get("wheel", [])}
    pin_wheels = {item["name"]: item for item in pins.get("wheel", [])}
    expected_names = {item["name"] for item in PINNED}
    if set(lock_wheels) != expected_names:
        errors.append(f"lock wheels {sorted(lock_wheels)} != {sorted(expected_names)}")
    if set(req) != expected_names:
        errors.append(f"requirements.lock names {sorted(req)} != {sorted(expected_names)}")
    if set(pin_wheels) != expected_names:
        errors.append(f"pins.toml wheels {sorted(pin_wheels)} != {sorted(expected_names)}")
    for spec in PINNED:
        name = spec["name"]
        locked = lock_wheels.get(name, {})
        pinned = pin_wheels.get(name, {})
        required = req.get(name, {})
        if locked.get("sha256") != required.get("sha256"):
            errors.append(f"{name}: requirements.lock sha256 != lock.json")
        if locked.get("sha256") != pinned.get("sha256"):
            errors.append(f"{name}: pins.toml sha256 != lock.json")
        if locked.get("version") != spec["version"]:
            errors.append(f"{name}: lock version {locked.get('version')!r} != {spec['version']!r}")
        if required.get("version") != spec["version"]:
            errors.append(f"{name}: requirements version {required.get('version')!r}")
        if locked.get("url") != spec["url"]:
            errors.append(f"{name}: lock url does not match the recorded PyPI wheel URL")
    expected_req = requirements_text(lock.get("wheel", []))
    if REQUIREMENTS.read_text(encoding="utf-8") != expected_req:
        errors.append("requirements.lock is not the lock.json rendering")
    expected_pins = pins_text(lock)
    if PINS.read_text(encoding="utf-8") != expected_pins:
        errors.append("pins.toml is not the lock.json rendering; run write-lock.py --write")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Write or check the Django ORM pin from wheel hashes")
    parser.add_argument("--write", action="store_true", help="hash wheels in --wheel-dir and rewrite lock files")
    parser.add_argument("--wheel-dir", type=Path, default=None, help="directory of downloaded wheels")
    parser.add_argument("--check", action="store_true", help="require lock.json, requirements.lock, and pins.toml to match")
    args = parser.parse_args()
    if args.write:
        if args.wheel_dir is None:
            print("S1 ORM FAIL-CLOSED: --write requires --wheel-dir", file=sys.stderr)
            return 2
        write_from_wheels(args.wheel_dir)
        print(f"WROTE {LOCK} {REQUIREMENTS} {PINS}")
    if args.check or not args.write:
        errors = check_consistency()
        if errors:
            print("S1 ORM FAIL-CLOSED: lock/pin mismatch", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
            return 2
        print("S1 ORM LOCK OK django=5.2.17 paper_s1=unexecuted mutation_score=not-stored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
