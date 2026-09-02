# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from .certificate import certificate_payload_from_records, render_certificate
from .evidence import append_record, load_records


def _paths(run: Path) -> tuple[Path, Path]:
    run = run.resolve()
    log, queue = run / "evidence.jsonl", run / "survivors.json"
    if not log.exists() or not queue.exists():
        raise ValueError(f"{run} is not a certification run with a survivor queue")
    return log, queue


def _queue(run: Path) -> list[dict[str, str]]:
    _, queue_path = _paths(run)
    value = json.loads(queue_path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("survivors.json must be a list")
    return value


def _write_queue(run: Path, queue: list[dict[str, str]]) -> None:
    _, queue_path = _paths(run)
    queue_path.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _refresh_certificate(run: Path) -> None:
    log, _ = _paths(run)
    records = load_records(log)
    config = next(record for record in reversed(records) if record["type"] == "CONFIG")
    payload = certificate_payload_from_records(records, {"type": "CERTIFICATE", "payload": {"config_hash": config["hash"]}})
    certificate = append_record(log, "CERTIFICATE", payload)
    (run / "certificate.txt").write_text(render_certificate(payload, config, certificate["hash"]), encoding="utf-8")


def set_class(run: Path, mutant_id: str, classification: str) -> None:
    log, _ = _paths(run)
    queue = _queue(run)
    entry = next((item for item in queue if item.get("mutant_id") == mutant_id), None)
    if entry is None:
        raise ValueError(f"{mutant_id} is not a survivor in this run")
    entry["classification"] = classification
    _write_queue(run, queue)
    append_record(log, "TRIAGE", {"mutant_id": mutant_id, "classification": classification})
    _refresh_certificate(run)


def add_override(
    run: Path,
    mutant_id: str,
    name: str,
    reason_code: str,
    justification: str,
    *,
    evidence_ref: str | None = None,
    approval_ref: str | None = None,
) -> None:
    log, _ = _paths(run)
    queue = _queue(run)
    entry = next((item for item in queue if item.get("mutant_id") == mutant_id), None)
    if entry is None:
        raise ValueError(f"{mutant_id} is not a survivor in this run")
    payload: dict[str, str] = {"mutant_id": mutant_id, "name": name, "reason_code": reason_code, "justification": justification}
    if reason_code == "EQUIVALENT_BY_INSPECTION":
        if not (evidence_ref and evidence_ref.strip()):
            raise ValueError("EQUIVALENT_BY_INSPECTION requires an evidence_ref")
        classification = "EQUIVALENT"
    else:
        classification = "SIGNED_RESIDUAL"
    if evidence_ref and evidence_ref.strip():
        payload["evidence_ref"] = evidence_ref.strip()
    if approval_ref and approval_ref.strip():
        payload["approval_ref"] = approval_ref.strip()
    append_record(log, "OVERRIDE", payload)
    append_record(log, "TRIAGE", {"mutant_id": mutant_id, "classification": classification})
    entry["classification"] = classification
    _write_queue(run, queue)
    _refresh_certificate(run)


def show_queue(run: Path) -> str:
    return json.dumps(_queue(run), indent=2, sort_keys=True) + "\n"
