#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the Django ORM pin files. This is not a mutation score."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ORM = Path(__file__).resolve().parent
WRITE_LOCK = ORM / "write-lock.py"


def main() -> int:
    result = subprocess.run(
        [sys.executable, str(WRITE_LOCK), "--check"],
        cwd=ORM.parent.parent.parent,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
