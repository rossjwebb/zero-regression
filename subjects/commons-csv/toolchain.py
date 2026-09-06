# SPDX-License-Identifier: Apache-2.0
"""S2 toolchain helpers: JDK isolation, JAR pins, classfile gate, PIT log judge.

Never compute or store a mutation score.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
import tarfile
import tomllib
import urllib.request
from pathlib import Path

SUBJECT = Path(__file__).resolve().parent
PINS = SUBJECT / "pins.toml"

# Java 8 classfile major version. Subject bytecode must stay here.
JAVA8_MAJOR = 52

ABNORMAL = ("TIMED_OUT", "MEMORY_ERROR", "RUN_ERROR")

# Keys that would smuggle a kill-rate into a score-free receipt.
FORBIDDEN_NUMERIC_KEYS = frozenset(
    {
        "kill_rate",
        "killed",
        "seeded",
        "survivors",
        "mutation_percent",
        "mutations_generated",
        "mutations_killed",
        "mutations_survived",
        "score",
    }
)

# Text that would store a mutation % or kill-rate. The field
# mutation_score=not-stored is allowed; a numeric assignment is not.
SCORE_TEXT_RE = re.compile(
    r"killed\s*/\s*seeded|"
    r"generated\s+\d+\s+mutations|"
    r"\(\s*\d+(?:\.\d+)?\s*%\s*\)|"
    r"mutation_score\s*[:=]\s*\d",
    re.IGNORECASE,
)


def load_pins() -> dict:
    with PINS.open("rb") as handle:
        return tomllib.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"S2 FAIL-CLOSED: {message}")


def ensure_jars(lib: Path, pins: dict | None = None) -> dict[str, Path]:
    pins = pins or load_pins()
    lib.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    for jar in pins["jar"]:
        dest = lib / f"{jar['artifact']}-{jar['version']}.jar"
        if not (dest.is_file() and sha256_file(dest) == jar["sha256"]):
            print(f"fetch {jar['url']}", file=sys.stderr)
            try:
                urllib.request.urlretrieve(jar["url"], dest)
            except Exception as exc:  # noqa: BLE001
                fail(f"download failed for {jar['url']}: {exc}")
            observed = sha256_file(dest)
            if observed != jar["sha256"]:
                fail(f"jar hash mismatch {dest.name}: expected {jar['sha256']} observed {observed}")
        print(f"jar ok {dest.name}", file=sys.stderr)
        found[jar["artifact"]] = dest
    return found


def _java_version_text(java_bin: Path) -> str:
    import subprocess

    completed = subprocess.run(
        [str(java_bin), "-version"],
        check=False,
        capture_output=True,
        text=True,
    )
    return (completed.stderr or "") + (completed.stdout or "")


def _is_pinned_jdk11(version_text: str, pins: dict) -> bool:
    marker = pins["jdk"]["version_marker"]
    return marker in version_text and "11." in version_text


def _extract_jdk(tarball: Path, dest_root: Path) -> Path:
    dest_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "r:gz") as archive:
        archive.extractall(dest_root)
    java_bins = list(dest_root.glob("*/bin/java"))
    if len(java_bins) != 1:
        fail(f"expected one JDK tree under {dest_root}, found {java_bins}")
    return java_bins[0].resolve().parent.parent


def ensure_jdk(work: Path, pins: dict | None = None) -> Path:
    """Return JAVA_HOME for the pinned JDK 11. Never use PATH java/javac.

    S2_JAVA_HOME may be set only if that tree is the pinned 11.0.32.1 marker.
    Otherwise the Adoptium tarball is fetched and hash-checked.
    """
    pins = pins or load_pins()
    override = os.environ.get("S2_JAVA_HOME", "").strip()
    if override:
        home = Path(override)
        java_bin = home / "bin" / "java"
        javac_bin = home / "bin" / "javac"
        if not java_bin.is_file() or not javac_bin.is_file():
            fail(f"S2_JAVA_HOME={override} is missing bin/java or bin/javac")
        text = _java_version_text(java_bin)
        if not _is_pinned_jdk11(text, pins):
            fail(
                f"S2_JAVA_HOME is not the pinned JDK {pins['jdk']['release']}. "
                f"Observed: {text.strip()!r}. Unset S2_JAVA_HOME to fetch the pin."
            )
        print(f"jdk override ok {home} ({pins['jdk']['release']})", file=sys.stderr)
        return home.resolve()

    jdk_cfg = pins["jdk"]
    tarball = work / "lib" / jdk_cfg["filename"]
    dest_root = work / "jdk"
    stamp = dest_root / ".sha256"
    if dest_root.is_dir() and stamp.is_file() and stamp.read_text(encoding="utf-8").strip() == jdk_cfg["sha256"]:
        homes = list(dest_root.glob("*/bin/java"))
        if len(homes) == 1:
            home = homes[0].resolve().parent.parent
            text = _java_version_text(home / "bin" / "java")
            if _is_pinned_jdk11(text, pins):
                print(f"jdk cache ok {home}", file=sys.stderr)
                return home

    dest_root.mkdir(parents=True, exist_ok=True)
    tarball.parent.mkdir(parents=True, exist_ok=True)
    if not (tarball.is_file() and sha256_file(tarball) == jdk_cfg["sha256"]):
        print(f"fetch {jdk_cfg['url']}", file=sys.stderr)
        try:
            urllib.request.urlretrieve(jdk_cfg["url"], tarball)
        except Exception as exc:  # noqa: BLE001
            fail(f"JDK download failed for {jdk_cfg['url']}: {exc}")
        observed = sha256_file(tarball)
        if observed != jdk_cfg["sha256"]:
            fail(f"JDK hash mismatch: expected {jdk_cfg['sha256']} observed {observed}")
    print(f"jdk tarball ok {tarball.name}", file=sys.stderr)
    if dest_root.exists():
        shutil.rmtree(dest_root)
    home = _extract_jdk(tarball, dest_root)
    stamp.write_text(jdk_cfg["sha256"] + "\n", encoding="utf-8")
    text = _java_version_text(home / "bin" / "java")
    if not _is_pinned_jdk11(text, pins):
        fail(f"extracted JDK is not {jdk_cfg['release']}: {text.strip()!r}")
    print(f"jdk ok {home}", file=sys.stderr)
    return home


def classfile_major(path: Path) -> int:
    data = path.read_bytes()
    if data[:4] != b"\xca\xfe\xba\xbe":
        fail(f"{path} is not a Java class file")
    return int.from_bytes(data[6:8], "big")


def assert_java8_classfiles(classes_dir: Path, relative_paths: list[str]) -> None:
    for rel in relative_paths:
        path = classes_dir / rel
        if not path.is_file():
            fail(f"missing class file {rel}")
        major = classfile_major(path)
        if major != JAVA8_MAJOR:
            fail(
                f"{rel} classfile major {major} (want {JAVA8_MAJOR} / Java 8). "
                "Toolchain mixed with a later --release."
            )
        print(f"classfile ok {rel} major={major}", file=sys.stderr)


def judge_pit_log(log_text: str) -> list[str]:
    """Return fail-closed reasons. Does not compute a mutation score."""
    errors: list[str] = []
    if "Created 0 mutation test units" in log_text:
        errors.append("PIT created no mutation test units")
    if "No mutations found" in log_text:
        errors.append("PIT found no mutations")
    if "is not a recognized option" in log_text or "show help" in log_text:
        errors.append("PIT rejected the command line (unrecognized option or help)")
    if "Minion exited abnormally" in log_text or "MINION_DIED" in log_text:
        errors.append("PIT minion exited abnormally")
    for kind in ABNORMAL:
        counts = [int(match) for match in re.findall(rf"\b{kind}\s+(\d+)\b", log_text)]
        if any(count > 0 for count in counts):
            errors.append(f"PIT reported {kind} (isolated per mutant; run is not a success)")
    return errors


def contains_forbidden_score_text(text: str) -> bool:
    """True if text would store a kill-rate or mutation percentage."""
    return bool(SCORE_TEXT_RE.search(text))


def receipt_score_errors(node: object, prefix: str = "") -> list[str]:
    """Walk a receipt/posture tree. Reject numeric scores and kill-rate keys."""
    errors: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{prefix}.{key}" if prefix else key
            if key == "mutation_score":
                if isinstance(value, (int, float)):
                    errors.append(f"{here} must not be numeric")
                elif value not in ("not-stored", None):
                    errors.append(f"{here}: expected 'not-stored' got {value!r}")
            if key in FORBIDDEN_NUMERIC_KEYS and isinstance(value, (int, float)):
                errors.append(f"{here} must not be numeric")
            errors.extend(receipt_score_errors(value, here))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            errors.extend(receipt_score_errors(item, f"{prefix}[{index}]"))
    elif isinstance(node, str) and contains_forbidden_score_text(node):
        errors.append(f"{prefix or 'text'} stores a mutation-score claim")
    return errors


def classify_live_work(
    work: Path,
    pit_rc: int | None = None,
) -> tuple[bool, str | None, list[str]]:
    """Classify a run-pit.sh work tree without reading a mutation score.

    Returns (executed, blocked, judge_errors). blocked is a token, not a
    skip-as-pass. Missing work is blocked=pit-not-run.
    """
    html = work / "pit-reports" / "index.html"
    log = work / "pit.log"
    if pit_rc is None and not log.is_file() and not html.is_file():
        return False, "pit-not-run", []

    judge_errors: list[str] = []
    if log.is_file():
        judge_errors = judge_pit_log(log.read_text(encoding="utf-8", errors="replace"))
    elif pit_rc == 0:
        judge_errors = ["PIT log is missing; cannot judge TIMED_OUT / MEMORY_ERROR / RUN_ERROR"]

    if pit_rc is not None and pit_rc != 0:
        return False, f"pit-process-exit-{pit_rc}", judge_errors
    if judge_errors:
        return False, "pit-judge-fail-closed", judge_errors
    if not html.is_file():
        return False, "pit-html-missing", judge_errors
    return True, None, []


def build_live_receipt(
    *,
    pins: dict,
    work: Path,
    python_version: str,
    pit_rc: int | None = None,
    html_report_tracked: bool = False,
) -> dict:
    """Build a score-free receipt from a live work tree.

    Never copies pit.log or the HTML report body. Those files contain
    PIT's own kill counts. This receipt only records process facts.
    """
    executed, blocked, judge_errors = classify_live_work(work, pit_rc=pit_rc)
    html = work / "pit-reports" / "index.html"
    log = work / "pit.log"
    pit = pins["pit"]
    jdk = pins["jdk"]
    receipt = {
        "kind": "s2-commons-csv-pit-receipt",
        "subject": "commons-csv",
        "mutation_score": "not-stored",
        "paper_s2": "unexecuted",
        "status": "live-pit-executed" if executed else f"blocked={blocked}",
        "executed": executed,
        "blocked": blocked,
        "python": python_version,
        "pit_process_exit": pit_rc,
        "judge_errors": list(judge_errors),
        "judge": "subjects/commons-csv/toolchain.py:judge_pit_log",
        "html_report_present": html.is_file(),
        "html_report": "subjects/commons-csv/work/pit-reports/index.html",
        "html_report_gitignored": True,
        "html_report_tracked": html_report_tracked,
        "html_report_body_stored": False,
        "pit_log_present": log.is_file(),
        "pit_log_body_stored": False,
        "records_mutation_score": False,
        "green_suite": "passed" if executed or (pit_rc == 0 and not judge_errors) else "not-claimed",
        "classfile_major": JAVA8_MAJOR,
        "pins": {
            "defects4j": {
                "tag": pins["defects4j"]["tag"],
                "commit": pins["defects4j"]["commit"],
                "project": pins["defects4j"]["project"],
                "version": pins["defects4j"]["version"],
            },
            "commons_csv": {"commit": pins["commons_csv"]["commit"]},
            "pit": {
                "tool": pit["tool"],
                "version": pit["version"],
                "mutators": pit["mutators"],
                "subject_release": pit["subject_release"],
                "target_class": pit["target_class"],
            },
            "jdk": {
                "vendor": jdk["vendor"],
                "release": jdk["release"],
                "sha256": jdk["sha256"],
            },
        },
        "claims": {
            "mutation_score": "not-stored",
            "paper_s2": "unexecuted",
            "records_mutation_score": False,
        },
    }
    errors = receipt_score_errors(receipt)
    if errors:
        fail("receipt would store a mutation score: " + "; ".join(errors))
    return receipt
