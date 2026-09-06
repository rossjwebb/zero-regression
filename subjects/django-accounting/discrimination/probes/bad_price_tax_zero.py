# SPDX-License-Identifier: Apache-2.0
"""Known-bad: Price.tax is always zero and incl_tax ignores tax.

Patches ``accounting.libs.prices.Price`` after the pin module is
imported. Does not edit ``legacy/``. The 27-trace replay already
reads ``Price.tax`` on ``price_from_tax`` / ``price_from_incl``.
"""
from __future__ import annotations

from decimal import Decimal

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from accounting.libs.prices import Price

    def _get_tax(self: object) -> Decimal:
        return Decimal("0")

    def _set_tax(self: object, value: object) -> None:
        self.incl_tax = self.excl_tax
        self.is_tax_known = True

    original_init = Price.__init__

    def _init(self, currency, excl_tax, incl_tax=None, tax=None):
        if tax is not None and incl_tax is None:
            # Wrong incl_tax: drop the supplied tax amount.
            original_init(self, currency, excl_tax, incl_tax=excl_tax)
            return
        original_init(self, currency, excl_tax, incl_tax=incl_tax, tax=tax)

    Price.__init__ = _init
    Price.tax = property(_get_tax, _set_tax)
    _INSTALLED = True
