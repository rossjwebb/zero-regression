# SPDX-License-Identifier: Apache-2.0
"""Read mutmut 3.6.0 mutants/ output into MUTANT_RESULT rows."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# Copied from mutmut 3.6.0 status_by_exit_code (later duplicate of -24 wins: timeout).
STATUS_BY_EXIT_CODE: dict[int | None, str] = {
    1: "killed",
    3: "killed",
    0: "survived",
    5: "no tests",
    2: "check was interrupted by user",
    None: "not checked",
    33: "no tests",
    34: "skipped",
    35: "suspicious",
    36: "timeout",
    37: "caught by type check",
    -24: "timeout",
    24: "timeout",
    152: "timeout",
    255: "timeout",
    -11: "segfault",
    -9: "segfault",
}

OUTCOME_BY_STATUS = {
    "killed": "KILLED",
    "survived": "SURVIVED",
    "timeout": "TIMEOUT",
    "suspicious": "SUSPICIOUS",
    "skipped": "SKIPPED",
    "no tests": "SKIPPED",
    "not checked": "SKIPPED",
    "caught by type check": "KILLED",
    "check was interrupted by user": "SUSPICIOUS",
    "segfault": "SUSPICIOUS",
}

MUTANT_SELECTION_ENV = "MUTANT_UNDER_TEST"
CLASS_NAME_SEPARATOR = "ǁ"
RESULTS_LINE = re.compile(r"^\s*(.+):\s+([a-z][a-z ]+)\s*$")
FAILED_LINE = re.compile(r"^FAILED\s+(\S+)")


def outcome_from_exit_code(exit_code: int | None) -> str:
    status = STATUS_BY_EXIT_CODE.get(exit_code, "suspicious")
    return OUTCOME_BY_STATUS.get(status, "SUSPICIOUS")


def outcome_from_status(status: str) -> str:
    return OUTCOME_BY_STATUS.get(status.strip().lower(), "SUSPICIOUS")


def parse_mutant_key(key: str) -> tuple[str, str, str]:
    module, _, rest = key.partition(".")
    if CLASS_NAME_SEPARATOR in rest:
        parts = rest.split(CLASS_NAME_SEPARATOR)
        class_name = parts[1] if len(parts) >= 3 else ""
        function = parts[-1].partition("__mutmut_")[0]
    else:
        class_name = ""
        function = rest.partition("__mutmut_")[0].removeprefix("x_")
    return module, class_name, function


def location_for_key(key: str) -> str:
    module, class_name, function = parse_mutant_key(key)
    qualified = ".".join(part for part in (module, class_name, function) if part)
    return f"{qualified} · {key}"


def operator_for_key(key: str) -> str:
    suffix = key.rpartition("__mutmut_")[2]
    return f"mutmut_{suffix}" if suffix else "mutmut"


def _row(index: int, key: str, outcome: str) -> dict[str, Any]:
    mutant_id = str(index)
    return {
        "id": mutant_id,
        "mutant_id": mutant_id,
        "mutmut_key": key,
        "location": location_for_key(key),
        "operator": operator_for_key(key),
        "outcome": outcome,
        "failing_test": None,
        "killing_test": None,
    }


def load_meta_pairs(mutants_dir: Path) -> list[tuple[str, int | None]]:
    pairs: list[tuple[str, int | None]] = []
    for meta_path in sorted(mutants_dir.rglob("*.meta")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for key, exit_code in meta.get("exit_code_by_key", {}).items():
            pairs.append((key, exit_code))
    pairs.sort(key=lambda item: item[0])
    return pairs


def parse_results_text(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in text.splitlines():
        match = RESULTS_LINE.match(line)
        if not match:
            continue
        pairs.append((match.group(1).strip(), match.group(2).strip()))
    pairs.sort(key=lambda item: item[0])
    return pairs


def rows_from_mutants_dir(mutants_dir: Path, results_text: str = "") -> tuple[list[dict[str, Any]], str]:
    """Prefer per-module .meta JSON; otherwise parse `mutmut results` text."""
    mutants_dir = mutants_dir.resolve()
    meta_pairs = load_meta_pairs(mutants_dir)
    if meta_pairs:
        rows = [_row(index, key, outcome_from_exit_code(exit_code)) for index, (key, exit_code) in enumerate(meta_pairs, 1)]
        return rows, "meta"
    result_pairs = parse_results_text(results_text)
    if not result_pairs:
        raise ValueError(f"{mutants_dir}: no *.meta files and no parseable mutmut results text")
    rows = [_row(index, key, outcome_from_status(status)) for index, (key, status) in enumerate(result_pairs, 1)]
    return rows, "mutmut results"


def first_failing_test(output: str, junit_path: Path | None = None) -> str | None:
    for line in output.splitlines():
        match = FAILED_LINE.match(line.strip())
        if match:
            return match.group(1)
    if junit_path is not None and junit_path.exists():
        root = ET.parse(junit_path).getroot()
        for case in root.iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                classname = case.attrib.get("classname", "")
                name = case.attrib.get("name", "")
                return f"{classname}::{name}" if classname else name
    return None


def populate_failing_tests(
    rows: list[dict[str, Any]],
    mutants_dir: Path,
    test_paths: list[str],
    *,
    executable: str | None = None,
) -> str:
    """Re-run pytest -x -q under MUTANT_UNDER_TEST for each KILLED mutant.

    Returns the selection-env name on success, or KILLING_TEST_UNAVAILABLE.
    """
    mutants_dir = mutants_dir.resolve()
    python = executable or sys.executable
    killed = [row for row in rows if row["outcome"] == "KILLED"]
    if not killed:
        return MUTANT_SELECTION_ENV
    populated = 0
    for row in killed:
        junit = mutants_dir / ".kill-junit.xml"
        command = [python, "-m", "pytest", "-x", "-q", "--tb=no", f"--junitxml={junit}", *test_paths]
        env = {**os.environ, "PYTHONHASHSEED": "0", MUTANT_SELECTION_ENV: row["mutmut_key"]}
        result = subprocess.run(command, cwd=mutants_dir, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        failing = first_failing_test(result.stdout, junit)
        row["failing_test"] = failing
        row["killing_test"] = failing
        if failing:
            populated += 1
        if junit.exists():
            junit.unlink()
    return MUTANT_SELECTION_ENV if populated else "KILLING_TEST_UNAVAILABLE"


def classify_from_diff(diff: str, key: str) -> tuple[str, str]:
    """Propose a survivor class and one sentence. Does not change subject code."""
    function = parse_mutant_key(key)[2]
    if re.search(r"elif \w+ > ", diff) and re.search(r"elif \w+ >= ", diff):
        return "EQUIVALENT", f"{function}: the elif sits after an exclusive equality branch, so >= is the same as >."
    if re.search(r'Decimal\("0\.00"\)', diff) and re.search(r"= None", diff):
        return "EQUIVALENT", f"{function}: the mutated initializer is overwritten on every path that later reads the name."
    if re.search(r"\bNone\b", diff) and re.search(r"\.(lock_account|get_by_accounts_code_no)\(", diff):
        return "UNDER_INVESTIGATION", f"{function}: a repository call argument was replaced with None; tests may not assert that argument."
    if re.search(r" < ", diff) and re.search(r" <= ", diff):
        return "UNDER_INVESTIGATION", f"{function}: a strict inequality became inclusive; tests may not distinguish the boundary."
    return "UNDER_INVESTIGATION", f"{function}: survivor at {key}; no automatic class beyond location."


def propose_triage(row: dict[str, Any], subject: Path, executable: str | None = None) -> tuple[str, str]:
    python = executable or sys.executable
    result = subprocess.run(
        [python, "-m", "mutmut", "show", row["mutmut_key"]],
        cwd=subject,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return classify_from_diff(result.stdout, row["mutmut_key"])
    return "UNDER_INVESTIGATION", f"Survivor {row['mutant_id']} at {row['location']}."
