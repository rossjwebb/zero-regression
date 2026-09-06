# SPDX-License-Identifier: Apache-2.0
"""Known-bad: unknown Price.tax returns zero instead of TypeError.

Patches ``accounting.libs.prices.Price.tax`` after the pin module is
imported. Does not edit ``legacy/``. Distinct from
``bad_price_tax_zero``: that probe zeros a *known* tax. This one
hides the unknown-tax access error already recorded on
``price_unknown_tax_access``.
"""
from __future__ import annotations

from decimal import Decimal

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from accounting.libs.prices import Price

    original = Price.tax

    def _get_tax(self: object) -> Decimal:
        if not getattr(self, "is_tax_known", False):
            return Decimal("0")
        return self.incl_tax - self.excl_tax

    Price.tax = property(_get_tax, original.fset)
    _INSTALLED = True
