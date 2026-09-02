# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
from typing import Any

from .evidence import load_records, verify_log


def _logs(roots: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for root in roots:
        if root.name == "evidence.jsonl":
            found.add(root)
        elif root.is_dir():
            found.update(root.rglob("evidence.jsonl"))
    return sorted(found)


def _row(log: Path) -> dict[str, Any] | None:
    errors, _ = verify_log(log)
    if errors:
        return None
    records = load_records(log)
    certificate = next(record for record in reversed(records) if record["type"] == "CERTIFICATE")
    payload = certificate["payload"]
    config = next(record for record in records if record["type"] == "CONFIG" and record["hash"] == payload["config_hash"])
    baseline = next(record for record in records if record["type"] == "BASELINE")
    summary = payload["summary"]
    mutation_runtime = next((record["payload"].get("mutation_stage_runtime_seconds", 0) for record in records if record["type"] == "MUTANT_RESULT" and "mutation_stage_runtime_seconds" in record["payload"]), 0)
    return {"subject": config["payload"]["subject"], "loc": baseline["payload"]["coverage"]["statements"], "tests": baseline["payload"]["tests"]["tests"], "coverage": baseline["payload"]["coverage"]["percent"], "mutants": summary["mutants"], "killed": summary["killed"], "survived": summary["survived"], "timeouts": summary["timeouts"], "kill_rate": 100 * summary["killed"] / summary["mutants"], "runtime": baseline["payload"]["runtime_seconds"] + mutation_runtime, "classes": summary["survivor_classes"]}


def render_results(roots: list[Path]) -> str:
    rows = [row for log in _logs(roots) if (row := _row(log)) is not None]
    rows.sort(key=lambda row: row["subject"])
    header = "| Subject | LOC | Tests | Coverage | Mutants | Killed | Survived | Timeouts | Kill rate | Runtime | Survivor classes (E/GR/UI/SR) |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    body = "".join(f"| {row['subject']} | {row['loc']} | {row['tests']} | {row['coverage']:.1f}% | {row['mutants']} | {row['killed']} | {row['survived']} | {row['timeouts']} | {row['kill_rate']:.1f}% | {row['runtime']:.2f}s | {row['classes']['EQUIVALENT']}/{row['classes']['GAP_REMEDIATED']}/{row['classes']['UNDER_INVESTIGATION']}/{row['classes']['SIGNED_RESIDUAL']} |\n" for row in rows)
    return header + body
