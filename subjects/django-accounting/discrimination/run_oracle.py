#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the S1 oracle, optionally after installing a known-bad import hook.

``--probe golden_echo`` returns ``expected.json`` and never imports the
pin. Other probes patch pin callables via ``hook.install_probe``.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

DISCRIMINATION = Path(__file__).resolve().parent
SUBJECT = DISCRIMINATION.parent
ORACLE = SUBJECT / "oracle.py"


def load_oracle():
    spec = importlib.util.spec_from_file_location("django_accounting_oracle", ORACLE)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {ORACLE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="S1 oracle runner with optional known-bad probe")
    parser.add_argument("--probe", default=None, help="known-bad probe name or golden_echo")
    args = parser.parse_args()
    if str(DISCRIMINATION) not in sys.path:
        sys.path.insert(0, str(DISCRIMINATION))

    if args.probe == "golden_echo":
        from probes.golden_echo import main as echo_main

        return echo_main()

    if args.probe:
        from hook import install_probe

        install_probe(args.probe)

    oracle = load_oracle()
    saved_argv = sys.argv
    sys.argv = [str(ORACLE)]
    try:
        return oracle.main()
    finally:
        sys.argv = saved_argv



if __name__ == "__main__":
    raise SystemExit(main())
