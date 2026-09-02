# SPDX-License-Identifier: Apache-2.0
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc)
