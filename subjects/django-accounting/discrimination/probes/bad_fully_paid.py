# SPDX-License-Identifier: Apache-2.0
"""Known-bad: invert AbstractSale.is_fully_paid.

Patches the pin class after import. Does not edit ``legacy/``.
The 27-trace replay already calls ``is_fully_paid`` on paid and
unpaid invoices.
"""
from __future__ import annotations

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from accounting.apps.books.models import AbstractSale

    original = AbstractSale.is_fully_paid

    def is_fully_paid(self):
        return not original(self)

    AbstractSale.is_fully_paid = is_fully_paid
    _INSTALLED = True
