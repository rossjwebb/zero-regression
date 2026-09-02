# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .certificate import certificate_payload_from_records, render_certificate
from .evidence import append_record, canonical_json, load_records

try:  # Python 3.12 is enforced before a subject config is read.
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - permits an intelligible pin failure on older Python.
    tomllib = None  # type: ignore[assignment]

LOCKFILE_NAME = "requirements-certification.txt"
REQUIRED_PINS = ("python", "mutmut", "pytest", "pytest-cov")


def die(message: str) -> None:
    raise SystemExit(f"CERTIFICATION FAILURE: {message}")


def coverage_module_name(source_path: str) -> str:
    """Derive a pytest-cov module name from a file path, package path, or bare module."""
    path = source_path.replace("\\", "/").strip().rstrip("/")
    if path.endswith(".py"):
        path = path[: -len(".py")]
    return path.replace("/", ".")


def lockfile_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / LOCKFILE_NAME
        if candidate.is_file():
            return candidate
    die(f"cannot locate {LOCKFILE_NAME} above {here}")


def pins_from_lockfile(path: Path | None = None) -> dict[str, str]:
    lock = path or lockfile_path()
    pins: dict[str, str] = {}
    for raw in lock.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("#"):
            stripped = stripped[1:].strip()
        if "==" not in stripped:
            continue
        name, version = stripped.split("==", 1)
        name, version = name.strip(), version.strip()
        if name and version and " " not in name:
            pins[name] = version
    missing = [name for name in REQUIRED_PINS if name not in pins]
    if missing:
        die(f"{lock}: missing pins {', '.join(missing)}")
    return {name: pins[name] for name in REQUIRED_PINS}


def read_subject_config(subject: Path) -> dict[str, Any]:
    if tomllib is None:
        die("Python 3.12.3 is required (tomllib is unavailable in this interpreter)")
    config_path = subject / "zero-regression.toml"
    if not config_path.exists():
        die(f"missing {config_path}; see subjects/template.zero-regression.toml")
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    required = {"name", "source_paths", "test_paths", "operator_set", "unverified_scope"}
    missing = required - config.get("subject", {}).keys()
    if missing:
        die(f"{config_path}: [subject] missing {', '.join(sorted(missing))}")
    return config


def installed_versions() -> dict[str, str]:
    versions = {"python": platform.python_version()}
    for distribution, display in (("mutmut", "mutmut"), ("pytest", "pytest"), ("pytest-cov", "pytest-cov")):
        try:
            versions[display] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[display] = "NOT INSTALLED"
    return versions


def environment_payload() -> dict[str, Any]:
    versions = installed_versions()
    return {
        "versions": versions,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable": str(Path(sys.executable).resolve()),
        "environment_hash": hashlib.sha256(canonical_json({"versions": versions, "implementation": platform.python_implementation(), "platform": platform.platform()}).encode()).hexdigest(),
    }


def check_pins(pins: dict[str, str]) -> dict[str, Any]:
    environment = environment_payload()
    mismatches = [f"{name}={environment['versions'].get(name)!r} (requires {value!r})" for name, value in pins.items() if environment["versions"].get(name) != value]
    if mismatches:
        die("un-pinned environment: " + "; ".join(mismatches))
    return environment


def revision(path: Path) -> str:
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    digest = hashlib.sha256()
    candidates = [path] if path.is_file() else list(path.rglob("*"))
    for file in sorted(item for item in candidates if item.is_file() and ".git" not in item.parts and "evidence" not in item.parts):
        digest.update((file.name if path.is_file() else file.relative_to(path).as_posix()).encode())
        digest.update(b"\0")
        digest.update(file.read_bytes())
        digest.update(b"\0")
    return f"tree-sha256:{digest.hexdigest()}"


def run_command(args: list[str], cwd: Path, artifact: Path) -> tuple[int, float, str]:
    started = time.monotonic()
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, env={**os.environ, "PYTHONHASHSEED": "0"})
    duration = time.monotonic() - started
    artifact.write_text(result.stdout, encoding="utf-8")
    return result.returncode, duration, result.stdout


def junit_summary(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    # A nested testsuite double-counts; use the root attributes when available.
    suite = suites[0]
    tests = int(suite.attrib.get("tests", "0"))
    failures = int(suite.attrib.get("failures", "0"))
    errors = int(suite.attrib.get("errors", "0"))
    skipped = int(suite.attrib.get("skipped", "0"))
    return {"tests": tests, "failures": failures, "errors": errors, "skipped": skipped, "passed": tests - failures - errors - skipped}


def coverage_summary(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    totals = data["totals"]
    return {"covered": int(totals["covered_lines"]), "statements": int(totals["num_statements"]), "percent": float(totals["percent_covered"])}


def baseline(subject: Path, config: dict[str, Any], run: Path) -> dict[str, Any]:
    tests = list(config["subject"]["test_paths"])
    source_paths = list(config["subject"]["source_paths"])
    attempts: list[dict[str, Any]] = []
    for number in (1, 2):
        junit = run / f"baseline-{number}.junit.xml"
        coverage = run / f"coverage-{number}.json"
        command = [sys.executable, "-m", "pytest", *tests, "-q", f"--junitxml={junit}"]
        for path in source_paths:
            command.extend([f"--cov={coverage_module_name(path)}"])
        command.append(f"--cov-report=json:{coverage}")
        code, seconds, _ = run_command(command, subject, run / f"baseline-{number}.output.txt")
        if code != 0:
            die(f"BASELINE attempt {number} failed; inspect {run / f'baseline-{number}.output.txt'}")
        attempts.append({"summary": junit_summary(junit), "coverage": coverage_summary(coverage), "runtime_seconds": round(seconds, 6)})
    if attempts[0]["summary"] != attempts[1]["summary"] or attempts[0]["coverage"] != attempts[1]["coverage"]:
        die("BASELINE is non-deterministic (test result or coverage differed between attempts)")
    return {"attempts": attempts, "tests": attempts[0]["summary"], "coverage": attempts[0]["coverage"], "runtime_seconds": round(sum(a["runtime_seconds"] for a in attempts), 6), "deterministic": True}


def mutation_rows_from_junit(path: Path) -> list[dict[str, Any]]:
    """Parse mutmut's JUnit export, retaining its id/location metadata where emitted."""
    root = ET.parse(path).getroot()
    rows: list[dict[str, Any]] = []
    for case in root.iter("testcase"):
        name = case.attrib.get("name", "")
        classname = case.attrib.get("classname", "")
        mutant_id = re.search(r"(?:mutant|mutation)[ _#:-]*(\d+)", f"{classname} {name}", re.I)
        if not mutant_id:
            continue
        outcome = "SURVIVED"
        if case.find("failure") is not None or case.find("error") is not None:
            outcome = "KILLED"
        elif case.find("skipped") is not None:
            outcome = "TIMEOUT"
        rows.append({"id": mutant_id.group(1), "location": classname or "unknown", "operator": "mutmut", "outcome": outcome, "killing_test": name if outcome == "KILLED" else None})
    return rows


def mutation(subject: Path, run: Path) -> tuple[list[dict[str, Any]], float]:
    # mutmut's cache is deliberately moved into the evidence pack, never silently reused.
    cache = subject / "mutants"
    if cache.exists():
        archived = run / "mutmut-cache-before-run"
        shutil.move(str(cache), str(archived))
    code, duration, _ = run_command([sys.executable, "-m", "mutmut", "run"], subject, run / "mutmut-run.output.txt")
    if code not in (0, 1):
        die(f"mutmut failed with exit {code}; inspect {run / 'mutmut-run.output.txt'}")
    junit = run / "mutmut.junit.xml"
    export_code, _, _ = run_command([sys.executable, "-m", "mutmut", "junitxml", "--output", str(junit)], subject, run / "mutmut-junit.output.txt")
    if export_code != 0 or not junit.exists():
        die("mutmut did not produce JUnit XML; this version cannot be certified without a per-mutant adapter")
    rows = mutation_rows_from_junit(junit)
    if not rows or len({row["id"] for row in rows}) != len(rows):
        die("mutmut JUnit export did not provide one unique, parseable row per mutant")
    rows[0]["mutation_stage_runtime_seconds"] = round(duration, 6)
    if cache.exists():
        shutil.move(str(cache), str(run / "mutmut-cache-generated"))
    return rows, round(duration, 6)


def write_queue(run: Path, rows: list[dict[str, Any]]) -> None:
    survivors = [row for row in rows if row["outcome"] == "SURVIVED"]
    queue = [{"mutant_id": row["id"], "location": row["location"], "operator": row["operator"], "classification": "UNDER_INVESTIGATION"} for row in survivors]
    (run / "survivors.json").write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def certify(subject: Path) -> Path:
    subject = subject.resolve()
    pins = pins_from_lockfile()
    environment = check_pins(pins)
    config = read_subject_config(subject)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = subject / "evidence" / f"run-{stamp}-{uuid.uuid4().hex[:8]}"
    run.mkdir(parents=True)
    log = run / "evidence.jsonl"
    source_paths = [subject / path for path in config["subject"]["source_paths"]]
    test_paths = [subject / path for path in config["subject"]["test_paths"]]
    config_record = append_record(log, "CONFIG", {"subject": config["subject"]["name"], "source_revision": revision(subject), "suite_revision": hashlib.sha256(canonical_json([revision(path) for path in test_paths]).encode()).hexdigest(), "tools": pins, "executor": {"role": "Executor", "identity": f"{environment['implementation']} {environment['versions']['python']}", "executable": environment["executable"], "tools": pins}, "operator_set": config["subject"]["operator_set"], "unverified_scope": config["subject"]["unverified_scope"], "source_paths": [str(path.relative_to(subject)) for path in source_paths], "test_paths": [str(path.relative_to(subject)) for path in test_paths], "environment": environment})
    baseline_payload = baseline(subject, config, run)
    append_record(log, "BASELINE", baseline_payload)
    rows, mutation_runtime = mutation(subject, run)
    for row in rows:
        append_record(log, "MUTANT_RESULT", row)
    write_queue(run, rows)
    for row in rows:
        if row["outcome"] == "SURVIVED":
            append_record(log, "TRIAGE", {"mutant_id": row["id"], "classification": "UNDER_INVESTIGATION"})
    provisional = {"config_hash": config_record["hash"]}
    payload = certificate_payload_from_records(load_records(log), {"payload": provisional, "type": "CERTIFICATE"})
    certificate = append_record(log, "CERTIFICATE", payload)
    (run / "certificate.txt").write_text(render_certificate(payload, config_record, certificate["hash"]), encoding="utf-8")
    print(f"CERTIFIED: {run}")
    return run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Zero-Regression five-stage certification protocol")
    parser.add_argument("subject", type=Path)
    args = parser.parse_args()
    certify(args.subject)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
