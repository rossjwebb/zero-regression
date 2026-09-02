# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64
VALID_TYPES = {"CONFIG", "BASELINE", "MUTANT_RESULT", "TRIAGE", "OVERRIDE", "COST", "CERTIFICATE"}


def canonical_json(value: Any) -> str:
    """The byte-level canonical form used for all chain hashes."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def record_hash(record: dict[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "hash"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def load_records(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"seq {line_number}: blank rows are not permitted")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"seq {line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"seq {line_number}: record must be an object")
        records.append(record)
    return records


def append_record(log_path: Path, record_type: str, payload: dict[str, Any], *, timestamp: str | None = None) -> dict[str, Any]:
    if record_type not in VALID_TYPES:
        raise ValueError(f"unsupported record type: {record_type}")
    records = load_records(log_path)
    errors, _ = verify_records(records, allow_no_certificate=True)
    if errors:
        raise ValueError("refusing to append to invalid chain: " + "; ".join(errors))
    record: dict[str, Any] = {
        "seq": len(records) + 1,
        "ts": timestamp or datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "type": record_type,
        "payload": payload,
        "prev_hash": records[-1]["hash"] if records else GENESIS_HASH,
    }
    record["hash"] = record_hash(record)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(record) + "\n")
    return record


def verify_log(log_path: Path) -> tuple[list[str], dict[str, Any]]:
    try:
        records = load_records(log_path)
    except ValueError as exc:
        return [str(exc)], {"records": 0}
    return verify_records(records)


def verify_records(records: list[dict[str, Any]], *, allow_no_certificate: bool = False) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    prior = GENESIS_HASH
    for row, record in enumerate(records, 1):
        required = {"seq", "ts", "type", "payload", "prev_hash", "hash"}
        missing = required - record.keys()
        if missing:
            errors.append(f"seq {row}: missing fields {', '.join(sorted(missing))}")
            continue
        if record["seq"] != row:
            errors.append(f"seq {row}: seq is {record['seq']!r}, expected {row}")
        if record["type"] not in VALID_TYPES:
            errors.append(f"seq {row}: unknown record type {record['type']!r}")
        if not isinstance(record["payload"], dict):
            errors.append(f"seq {row}: payload must be an object")
        if record["prev_hash"] != prior:
            errors.append(f"seq {row}: prev_hash link break")
        try:
            expected_hash = record_hash(record)
        except (TypeError, ValueError) as exc:
            errors.append(f"seq {row}: cannot canonicalise: {exc}")
            expected_hash = None
        if expected_hash and record["hash"] != expected_hash:
            errors.append(f"seq {row}: hash mismatch")
        prior = record.get("hash", prior)
    certificates = [record for record in records if record.get("type") == "CERTIFICATE"]
    if not allow_no_certificate and not certificates:
        errors.append("seq ?: no CERTIFICATE record")
    if certificates:
        from .certificate import certificate_payload_from_records

        for certificate in certificates:
            try:
                expected = certificate_payload_from_records(records, certificate)
            except ValueError as exc:
                errors.append(f"seq {certificate.get('seq', '?')}: certificate cannot derive from chain: {exc}")
                continue
            if certificate["payload"] != expected:
                errors.append(f"seq {certificate['seq']}: certificate does not derive from chain")
    return errors, {"records": len(records), "certificates": len(certificates)}
