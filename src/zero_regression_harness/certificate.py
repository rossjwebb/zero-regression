# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections import Counter
from typing import Any


def _latest_run_records(records: list[dict[str, Any]], certificate: dict[str, Any]) -> list[dict[str, Any]]:
    config_hash = certificate.get("payload", {}).get("config_hash")
    config_positions = [index for index, record in enumerate(records) if record.get("type") == "CONFIG" and record.get("hash") == config_hash]
    if len(config_positions) != 1:
        raise ValueError("CONFIG hash does not resolve uniquely")
    # The issuer derives the payload immediately before appending its closing
    # record, so that in-memory candidate is intentionally not yet in records.
    cert_index = records.index(certificate) if certificate in records else len(records)
    if cert_index <= config_positions[0]:
        raise ValueError("certificate precedes its CONFIG")
    return records[config_positions[0] : cert_index]


def certificate_payload_from_records(records: list[dict[str, Any]], certificate: dict[str, Any]) -> dict[str, Any]:
    run = _latest_run_records(records, certificate)
    config = run[0]
    baselines = [record for record in run if record["type"] == "BASELINE"]
    if len(baselines) != 1:
        raise ValueError("exactly one BASELINE is required")
    baseline = baselines[0]["payload"]
    mutants = [record["payload"] for record in run if record["type"] == "MUTANT_RESULT"]
    if not mutants:
        raise ValueError("no MUTANT_RESULT records")
    outcomes = Counter(mutant.get("outcome") for mutant in mutants)
    if set(outcomes) - {"KILLED", "SURVIVED", "TIMEOUT", "SUSPICIOUS", "SKIPPED"}:
        raise ValueError("invalid mutant outcome")
    survivor_ids = {str(mutant.get("mutant_id") or mutant["id"]) for mutant in mutants if mutant.get("outcome") == "SURVIVED"}
    classes = {mutant_id: "UNDER_INVESTIGATION" for mutant_id in survivor_ids}
    signed: dict[str, dict[str, str]] = {}
    for record in run:
        payload = record["payload"]
        if record["type"] == "TRIAGE" and payload.get("mutant_id") in survivor_ids:
            classification = payload.get("classification")
            if classification not in {"EQUIVALENT", "GAP_REMEDIATED", "UNDER_INVESTIGATION", "SIGNED_RESIDUAL"}:
                raise ValueError("invalid survivor class")
            if classification == "SIGNED_RESIDUAL" and payload.get("mutant_id") not in signed:
                raise ValueError("SIGNED_RESIDUAL requires an earlier OVERRIDE")
            classes[payload["mutant_id"]] = classification
        if record["type"] == "OVERRIDE":
            mutant_id = payload.get("mutant_id")
            if mutant_id not in survivor_ids:
                raise ValueError("OVERRIDE does not name a survivor")
            required = {"name", "reason_code", "justification"}
            if not required <= payload.keys() or not all(isinstance(payload[key], str) and payload[key].strip() for key in required):
                raise ValueError("OVERRIDE lacks named human, reason code, or justification")
            signed[mutant_id] = {key: payload[key] for key in required}
            classes[mutant_id] = "SIGNED_RESIDUAL"
    class_counts = Counter(classes.values())
    coverage = baseline.get("coverage")
    if not isinstance(coverage, dict) or not {"covered", "statements", "percent"} <= coverage.keys():
        raise ValueError("BASELINE lacks coverage")
    seeded = len(mutants)
    killed = outcomes["KILLED"]
    coverage_text = f"{coverage['percent']:.1f}% line coverage ({coverage['covered']}/{coverage['statements']} statements)"
    kill_text = (
        f"{killed}/{seeded} killed ({(100 * killed / seeded):.1f}%); "
        f"survivor classes E={class_counts['EQUIVALENT']} / GR={class_counts['GAP_REMEDIATED']} / "
        f"UI={class_counts['UNDER_INVESTIGATION']} / SR={class_counts['SIGNED_RESIDUAL']}; "
        f"timeouts={outcomes['TIMEOUT']}; suspicious={outcomes['SUSPICIOUS']}; skipped={outcomes['SKIPPED']}"
    )
    unverified = config["payload"].get("unverified_scope", "not declared")
    return {
        "format_version": 1,
        "config_hash": config["hash"],
        "lines": {"coverage": coverage_text, "kill_rate": kill_text, "unverified": str(unverified)},
        "summary": {
            "coverage": coverage,
            "mutants": seeded,
            "killed": killed,
            "survived": outcomes["SURVIVED"],
            "timeouts": outcomes["TIMEOUT"],
            "survivor_classes": {key: class_counts[key] for key in ("EQUIVALENT", "GAP_REMEDIATED", "UNDER_INVESTIGATION", "SIGNED_RESIDUAL")},
            "runtime_seconds": baseline.get("runtime_seconds"),
        },
    }


def render_certificate(payload: dict[str, Any], config: dict[str, Any], certificate_hash: str) -> str:
    subject = config["payload"]
    pins = subject["tools"]
    tool_text = ", ".join(f"{name} {pins[name]}" for name in sorted(pins))
    return "\n".join(
        [
            "BEHAVIOURAL-PARITY CERTIFICATE  v1",
            f"Subject:     {subject['source_revision']} · Suite: {subject['suite_revision']}",
            f"Pinned:      {tool_text} · Operators: {subject['operator_set']}",
            f"Line 1 — COVERAGE:    {payload['lines']['coverage']}",
            f"Line 2 — KILL RATE:   {payload['lines']['kill_rate']}",
            f"Line 3 — UNVERIFIED:  {payload['lines']['unverified']}",
            f"Chain:       {payload['config_hash']} … {certificate_hash}",
            "Expiry:      valid only for the pinned artifact above; any change to code, tests, tools, versions or operators voids this certificate.",
            "",
        ]
    )
