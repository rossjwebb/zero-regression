# SPDX-License-Identifier: Apache-2.0
"""Golden-echo probe: return expected.json without calling the pin.

A memorized copy of the golden file can pass pure replay. The Stage C
invariant gate must reject this probe because the pin was never
executed. This file must not import ``accounting.*``.
"""
from __future__ import annotations

import json
from pathlib import Path

SUBJECT = Path(__file__).resolve().parents[2]
GOLDEN = SUBJECT / "golden" / "expected.json"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
PIN_EXECUTED = False


def run_payload() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def main() -> int:
    payload = run_payload()
    cases = payload.get("cases", {})
    print(f"ORACLE OK pin={PIN} cases={len(cases)} replay-only")
    return 0
