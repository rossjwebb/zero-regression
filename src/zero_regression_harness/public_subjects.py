# SPDX-License-Identifier: Apache-2.0
"""Public S1–S3 certify/verify paths.

These subjects do not use the mutmut five-stage protocol. They must not
invent a mutation score, a kill-rate certificate, or a paper S3 / IBM
VSAM claim.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SUBJECTS_DIR = REPO_ROOT / "subjects"

ALIASES = {
    "s1": "django-accounting",
    "s2": "commons-csv",
    "s3": "carddemo",
    "django-accounting": "django-accounting",
    "commons-csv": "commons-csv",
    "carddemo": "carddemo",
    "accounting-service": "accounting-service",
}

PUBLIC_PROTOCOLS = {
    "django-accounting": "s1",
    "commons-csv": "s2",
    "carddemo": "s3",
}

S1_PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
S1_ORACLE_OK = f"ORACLE OK pin={S1_PIN} cases=27 replay-only"
S1_GATES = (
    ("oracle", "oracle.py", S1_ORACLE_OK),
    ("discrimination", "check-discrimination.py", "DISCRIMINATION OK"),
    ("stage-d", "check-stage-d.py", "STAGE D OK"),
    ("orm", "check-orm.py", "S1 ORM POSTURE OK"),
)

NUMERIC_SCORE_KEYS = frozenset({"mutation_score", "kill_rate", "killed", "seeded", "survivors"})


def die(message: str, code: int = 2) -> int:
    print(f"CERTIFICATION FAILURE: {message}", file=sys.stderr)
    return code


def run_process(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd or REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env={**os.environ, "PYTHONHASHSEED": "0"},
    )


def _subject_name_from_text(text: str) -> str | None:
    key = text.strip().replace("\\", "/").rstrip("/")
    if not key:
        return None
    leaf = key.rsplit("/", 1)[-1].lower()
    return ALIASES.get(leaf)


def resolve_subject(raw: Path | str) -> Path:
    text = os.fspath(raw)
    named = _subject_name_from_text(text)
    if named:
        candidate = SUBJECTS_DIR / named
        if candidate.is_dir():
            return candidate.resolve()
    path = Path(text)
    for candidate in (path, REPO_ROOT / path):
        if candidate.is_dir() and (candidate / "zero-regression.toml").is_file():
            return candidate.resolve()
    raise ValueError(f"cannot resolve subject {text!r}; expected a subject directory or s1/s2/s3")


def read_subject_name(subject: Path) -> str:
    config_path = subject / "zero-regression.toml"
    if not config_path.is_file():
        raise ValueError(f"missing {config_path}")
    try:
        import tomllib
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ValueError("Python 3.12.3 is required (tomllib is unavailable)") from exc
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    name = config.get("subject", {}).get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"{config_path}: [subject] name is required")
    return name


def protocol_for(subject: Path) -> str:
    name = read_subject_name(subject)
    return PUBLIC_PROTOCOLS.get(name, "mutmut")


def looks_like_jsonl(path: Path) -> bool:
    return path.is_file() or path.suffix == ".jsonl"


def score_errors(node: object, prefix: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{prefix}.{key}" if prefix else key
            if key == "mutation_score" and value not in ("not-stored", "not-recorded", None):
                if isinstance(value, (int, float)):
                    errors.append(f"{here} must not be numeric")
                else:
                    errors.append(f"{here}: expected 'not-stored' got {value!r}")
            elif key in NUMERIC_SCORE_KEYS and isinstance(value, (int, float)):
                errors.append(f"{here} must not be numeric")
            errors.extend(score_errors(value, here))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            errors.extend(score_errors(item, f"{prefix}[{index}]"))
    return errors


def _unique(errors: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in errors:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must be a JSON object")
    return payload


def _print_gate_output(label: str, output: str) -> None:
    text = output.rstrip("\n")
    if text:
        print(text)


def _require_executable(path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing {path}. Skip is not a pass."]
    mode = path.stat().st_mode
    if not mode & stat.S_IXUSR:
        return [f"{path} is not executable. Skip is not a pass."]
    return []


def verify_s1(subject: Path) -> tuple[list[str], dict[str, Any]]:
    packs = (
        subject / "evidence" / "discrimination" / "posture.json",
        subject / "evidence" / "stage-d" / "posture.json",
        subject / "evidence" / "orm" / "posture.json",
        subject / "evidence" / "s1-part-b-posture.json",
    )
    errors: list[str] = []
    seen: dict[str, Any] = {}
    for path in packs:
        try:
            payload = load_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if payload.get("paper_s1") != "unexecuted":
            errors.append(f"{path.name}: paper_s1 must be unexecuted")
        if payload.get("mutation_score") != "not-stored":
            errors.append(f"{path.name}: mutation_score must be not-stored")
        if "kill_rate" in payload:
            errors.append(f"{path.name} must not store kill_rate")
        errors.extend(f"{path.name}: {item}" for item in score_errors(payload))
        seen[path.name] = payload
    english_paths = (
        subject / "evidence" / "EVIDENCE.md",
        subject / "evidence" / "discrimination" / "EVIDENCE.md",
        subject / "evidence" / "stage-d" / "EVIDENCE.md",
        subject / "evidence" / "orm" / "EVIDENCE.md",
    )
    for path in english_paths:
        if not path.is_file():
            errors.append(f"missing {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if "mutation_score=not-stored" not in text:
            errors.append(f"{path.name} missing mutation_score=not-stored")
        if "killed/seeded" in text.lower():
            errors.append(f"{path.name} must not state a killed/seeded score")
        if "generators succeeded" in text.lower():
            errors.append(f"{path.name} must not claim generators succeeded")
    return _unique(errors), seen


def verify_s2(subject: Path) -> tuple[list[str], dict[str, Any]]:
    posture_path = subject / "evidence" / "s2-posture.json"
    receipt_path = subject / "evidence" / "pit-receipt.json"
    english = subject / "evidence" / "EVIDENCE.md"
    errors: list[str] = []
    seen: dict[str, Any] = {}
    try:
        posture = load_json(posture_path)
        receipt = load_json(receipt_path)
    except ValueError as exc:
        return [str(exc)], {}
    seen["s2-posture.json"] = posture
    seen["pit-receipt.json"] = receipt
    for name, payload in (("posture", posture), ("receipt", receipt)):
        if payload.get("paper_s2") != "unexecuted":
            errors.append(f"{name}.paper_s2 must be unexecuted")
        if payload.get("mutation_score") != "not-stored":
            errors.append(f"{name}.mutation_score must be not-stored")
        errors.extend(f"{name}: {item}" for item in score_errors(payload))
    if posture.get("runner", {}).get("records_mutation_score") is not False:
        errors.append("posture.runner.records_mutation_score must be false")
    if receipt.get("records_mutation_score") is not False:
        errors.append("receipt.records_mutation_score must be false")
    if receipt.get("html_report_body_stored") is True:
        errors.append("receipt must not store the HTML body")
    if not english.is_file():
        errors.append(f"missing {english}")
    else:
        text = english.read_text(encoding="utf-8")
        if "mutation_score=not-stored" not in text:
            errors.append("EVIDENCE.md missing mutation_score=not-stored")
        if "paper_s2=unexecuted" not in text:
            errors.append("EVIDENCE.md missing paper_s2=unexecuted")
        if "killed/seeded" in text.lower():
            errors.append("EVIDENCE.md must not state a killed/seeded score")
    dumped = json.dumps({"posture": posture, "receipt": receipt})
    if "killed/seeded" in dumped.lower():
        errors.append("committed S2 pack invented a killed/seeded score")
    return _unique(errors), seen


def verify_s3(subject: Path) -> tuple[list[str], dict[str, Any]]:
    posture_path = subject / "evidence" / "s3-posture.json"
    receipt_path = subject / "evidence" / "job-receipt.json"
    english = subject / "evidence" / "EVIDENCE.md"
    errors: list[str] = []
    seen: dict[str, Any] = {}
    try:
        posture = load_json(posture_path)
        receipt = load_json(receipt_path)
    except ValueError as exc:
        return [str(exc)], {}
    seen["s3-posture.json"] = posture
    seen["job-receipt.json"] = receipt
    required = {
        "paper_s3": "unexecuted",
        "mutation_score": "not-stored",
        "posttran_job": "run",
        "executed_job": True,
        "status": "gnucobol-posttran-fixture-run",
        "runtime": "gnucobol-indexed-bdb-fixture",
        "ibm_vsam": False,
        "ibm_cics": False,
    }
    for key, expected in required.items():
        if posture.get(key) != expected:
            errors.append(f"posture.{key}: expected {expected!r} got {posture.get(key)!r}")
    runner = posture.get("runner") or {}
    if runner.get("executed_job") is not True:
        errors.append("runner.executed_job must be true")
    if runner.get("posttran_job") != "run":
        errors.append("runner.posttran_job must be run")
    if runner.get("runtime") != "gnucobol-indexed-bdb-fixture":
        errors.append("runner.runtime must be gnucobol-indexed-bdb-fixture")
    compile_runner = posture.get("compile_runner") or {}
    if compile_runner.get("posttran_job") != "not-run":
        errors.append("compile_runner.posttran_job must stay not-run")
    if receipt.get("paper_s3") != "unexecuted":
        errors.append("receipt.paper_s3 must be unexecuted")
    if receipt.get("mutation_score") != "not-stored":
        errors.append("receipt.mutation_score must be not-stored")
    if receipt.get("posttran_job") != "run":
        errors.append("receipt.posttran_job must be run")
    if receipt.get("runtime") != "gnucobol-indexed-bdb-fixture":
        errors.append("receipt.runtime must be gnucobol-indexed-bdb-fixture")
    if receipt.get("ibm_vsam") is not False:
        errors.append("receipt.ibm_vsam must be false")
    if receipt.get("records_mutation_score") is not False:
        errors.append("receipt.records_mutation_score must be false")
    errors.extend(score_errors(posture))
    errors.extend(score_errors(receipt))
    if not english.is_file():
        errors.append(f"missing {english}")
    else:
        text = english.read_text(encoding="utf-8")
        for needle in (
            "mutation_score=not-stored",
            "paper_s3=unexecuted",
            "posttran_job=run",
            "runtime=gnucobol-indexed-bdb-fixture",
            "executed_job=true",
            "ibm_vsam=false",
        ):
            if needle not in text:
                errors.append(f"EVIDENCE.md missing {needle!r}")
        if "killed/seeded" in text.lower():
            errors.append("EVIDENCE.md must not state a killed/seeded score")
        if "paper s3 executed" in text.lower():
            errors.append("EVIDENCE.md must not claim paper S3 executed")
    return _unique(errors), seen


def verify_public(subject: Path) -> int:
    protocol = protocol_for(subject)
    if protocol == "s1":
        errors, _ = verify_s1(subject)
        label = "S1"
        extra = "paper_s1=unexecuted mutation_score=not-stored"
    elif protocol == "s2":
        errors, _ = verify_s2(subject)
        label = "S2"
        extra = "mutation_score=not-stored paper_s2=unexecuted"
    elif protocol == "s3":
        errors, _ = verify_s3(subject)
        label = "S3"
        extra = (
            "posttran_job=run "
            "runtime=gnucobol-indexed-bdb-fixture "
            "paper_s3=unexecuted "
            "mutation_score=not-stored"
        )
    else:
        return die(f"{subject} is not a public S1–S3 subject; pass an evidence.jsonl chain")
    if errors:
        print(f"{label} VERIFY FAIL-CLOSED: committed posture is not honest", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 2
    print(f"OK: {subject} ({label} posture; {extra}; not a kill-rate certificate)")
    return 0


def certify_s1(subject: Path) -> int:
    errors: list[str] = []
    for name, filename, marker in S1_GATES:
        path = subject / filename
        if not path.is_file():
            errors.append(f"{name} gate missing ({path}). Skip is not a pass.")
            continue
        result = run_process([sys.executable, str(path)])
        _print_gate_output(name, result.stdout)
        if result.returncode != 0:
            errors.append(f"{name} gate exited {result.returncode}")
            continue
        if marker not in result.stdout:
            errors.append(f"{name} gate did not print {marker!r}")
        if "killed/seeded" in result.stdout.lower():
            errors.append(f"{name} gate invented a killed/seeded score")
        if name == "oracle" and result.stdout.splitlines()[:1] != [S1_ORACLE_OK]:
            errors.append(f"oracle stdout was not the replay-only OK line")
    if errors:
        print("S1 CERTIFY FAIL-CLOSED: public S1 gates failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 2
    print(
        "CERTIFY S1 OK "
        "gates=oracle,discrimination,stage-d,orm "
        "paper_s1=unexecuted "
        "mutation_score=not-stored "
        "domain_correctness=out_of_scope"
    )
    return 0


def certify_s2(subject: Path) -> int:
    gate = subject / "check-s2-pit.py"
    if not gate.is_file():
        return die("check-s2-pit.py is missing. Skip is not a pass.")
    result = run_process([sys.executable, str(gate)])
    _print_gate_output("s2", result.stdout)
    if result.returncode != 0:
        print("S2 CERTIFY FAIL-CLOSED: score-free PIT evidence gate failed", file=sys.stderr)
        if result.stdout:
            print(result.stdout, file=sys.stderr, end="" if result.stdout.endswith("\n") else "\n")
        return 2
    combined = result.stdout
    if "killed/seeded" in combined.lower() or "kill rate" in combined.lower():
        return die("S2 certify invented a mutation score")
    if "mutation_score=not-stored" not in combined:
        return die("S2 certify did not keep mutation_score=not-stored")
    if "paper_s2=unexecuted" not in combined:
        return die("S2 certify did not keep paper_s2=unexecuted")
    print("CERTIFY S2 OK mutation_score=not-stored paper_s2=unexecuted score-free")
    return 0


def _s3_kv_receipt(subject: Path, name: str) -> dict[str, str]:
    receipt = subject / "work" / name
    if not receipt.is_file():
        return {}
    values: dict[str, str] = {}
    for line in receipt.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def certify_s3(subject: Path) -> int:
    pin_gate = subject / "check-pins.py"
    if not pin_gate.is_file():
        return die("check-pins.py is missing. Skip is not a pass.")
    pins = run_process([sys.executable, str(pin_gate)])
    _print_gate_output("s3-pins", pins.stdout)
    if pins.returncode != 0 or not pins.stdout.startswith("S3 PIN OK"):
        print("S3 CERTIFY FAIL-CLOSED: pin check failed", file=sys.stderr)
        if pins.stdout:
            print(pins.stdout, file=sys.stderr, end="" if pins.stdout.endswith("\n") else "\n")
        return 2
    compile_runner = subject / "run-cobol.sh"
    job_runner = subject / "run-posttran.sh"
    errors = _require_executable(compile_runner) + _require_executable(job_runner)
    if errors:
        return die(errors[0])
    result = run_process([str(job_runner)])
    _print_gate_output("s3-posttran", result.stdout)
    combined = result.stdout
    if "killed/seeded" in combined.lower():
        return die("S3 certify invented a mutation score")
    cobc_fail = "S3 COBC FAIL" in combined or (subject / "work" / "COBC-FAIL").is_file()
    if cobc_fail:
        print(
            "CERTIFY S3 FAIL: GnuCOBOL compile error (S3 COBC FAIL). "
            "This is not posttran_job=run success.",
            file=sys.stderr,
        )
        return 1
    receipt = _s3_kv_receipt(subject, "POSTTRAN")
    job_ok = (
        result.returncode == 0
        and "S3 POSTTRAN OK" in combined
        and receipt.get("posttran_job") == "run"
        and receipt.get("runtime") == "gnucobol-indexed-bdb-fixture"
        and receipt.get("ibm_vsam") == "false"
        and receipt.get("paper_s3") == "unexecuted"
        and receipt.get("mutation_score") == "not-recorded"
        and receipt.get("program_return_code") == "4"
    )
    if job_ok:
        print(
            "CERTIFY S3 POSTTRAN OK "
            "posttran_job=run "
            "runtime=gnucobol-indexed-bdb-fixture "
            "paper_s3=unexecuted "
            "mutation_score=not-stored "
            "ibm_vsam=false "
            "executed_job=true"
        )
        return 0
    print("S3 CERTIFY FAIL-CLOSED: POSTTRAN job posture did not hold", file=sys.stderr)
    print(f"  runner_exit={result.returncode}", file=sys.stderr)
    return 2


def certify_public(subject: Path) -> int:
    protocol = protocol_for(subject)
    if protocol == "s1":
        return certify_s1(subject)
    if protocol == "s2":
        return certify_s2(subject)
    if protocol == "s3":
        return certify_s3(subject)
    return die(f"{subject} is not a public S1–S3 subject")
