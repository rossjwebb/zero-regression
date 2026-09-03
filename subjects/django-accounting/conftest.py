# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for path in (ROOT / "stubs", ROOT / "legacy"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
