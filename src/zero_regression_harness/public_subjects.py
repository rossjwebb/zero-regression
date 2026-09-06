# SPDX-License-Identifier: Apache-2.0
"""Public S1–S3 certify/verify paths.

These subjects do not use the mutmut five-stage protocol. They must not
invent a mutation score, a kill-rate certificate, or a POSTTRAN run.
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
    english = subject / "evidence" / "EVIDENCE.md"
    errors: list[str] = []
    try:
        posture = load_json(posture_path)
    except ValueError as exc:
        return [str(exc)], {}
    required = {
        "paper_s3": "unexecuted",
        "mutation_score": "not-stored",
        "posttran_job": "not-run",
        "executed_job": False,
        "status": "scaffolding+compile-runner-only",
    }
    for key, expected in required.items():
        if posture.get(key) != expected:
            errors.append(f"posture.{key}: expected {expected!r} got {posture.get(key)!r}")
    if posture.get("runner", {}).get("executed_job") is not False:
        errors.append("runner.executed_job must be false")
    if posture.get("runner", {}).get("posttran_job") != "not-run":
        errors.append("runner.posttran_job must be not-run")
    errors.extend(score_errors(posture))
    if not english.is_file():
        errors.append(f"missing {english}")
    else:
        text = english.read_text(encoding="utf-8")
        for needle in (
            "mutation_score=not-stored",
            "paper_s3=unexecuted",
            "posttran_job=not-run",
            "executed_job=false",
        ):
            if needle not in text:
                errors.append(f"EVIDENCE.md missing {needle!r}")
        if "killed/seeded" in text.lower():
            errors.append("EVIDENCE.md must not state a killed/seeded score")
        if "executed_job=true" in text.replace(" ", "").lower():
            errors.append("EVIDENCE.md must not set executed_job=true")
    return _unique(errors), posture


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
        extra = "posttran_job=not-run paper_s3=unexecuted mutation_score=not-stored"
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


def _s3_compile_receipt(subject: Path) -> dict[str, str]:
    receipt = subject / "work" / "COMPILE"
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
    runner = subject / "run-cobol.sh"
    errors = _require_executable(runner)
    if errors:
        return die(errors[0])
    result = run_process([str(runner)])
    _print_gate_output("s3-compile", result.stdout)
    combined = result.stdout
    if "killed/seeded" in combined.lower():
        return die("S3 certify invented a mutation score")
    cobc_fail = "S3 COBC FAIL" in combined or (subject / "work" / "COBC-FAIL").is_file()
    if cobc_fail:
        print(
            "CERTIFY S3 FAIL: GnuCOBOL compile error (S3 COBC FAIL). "
            "This is not posttran_job=not-run success.",
            file=sys.stderr,
        )
        return 1
    if result.returncode == 0:
        print(
            "S3 CERTIFY FAIL-CLOSED: compile-OK must not exit 0 "
            "(that would look like a passing POSTTRAN job)",
            file=sys.stderr,
        )
        return 2
    receipt = _s3_compile_receipt(subject)
    compile_ok = "S3 COMPILE OK" in combined
    harness_exit_2 = result.returncode == 2 and "S3 HARNESS EXIT 2" in combined
    job_not_run = (
        receipt.get("posttran_job") == "not-run"
        and receipt.get("result") == "compile-ok"
        and receipt.get("cobc_status") == "0"
        and receipt.get("harness_meaning") == "posttran-job-not-run"
    )
    if compile_ok and harness_exit_2 and job_not_run:
        print(
            "CERTIFY S3 COMPILE OK "
            "posttran_job=not-run "
            "paper_s3=unexecuted "
            "mutation_score=not-stored "
            "executed_job=false"
        )
        return 2
    print("S3 CERTIFY FAIL-CLOSED: compile posture did not hold", file=sys.stderr)
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
