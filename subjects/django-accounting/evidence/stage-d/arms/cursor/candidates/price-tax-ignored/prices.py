# SPDX-License-Identifier: Apache-2.0
"""Stage D Cursor candidate: intentional weak Price rewrite.

Drops tax. ``incl_tax`` is always equal to ``excl_tax`` when the
caller supplies a tax amount. ``Price.tax`` is always zero once tax
is treated as known. Applied via the Stage D import hook. Does not
edit legacy/. This file is not the pin and is not paper S1.
"""
from __future__ import annotations

from decimal import Decimal


class Price(object):
    """Weak rewrite: tax is ignored."""

    def __init__(self, currency, excl_tax, incl_tax=None, tax=None):
        self.currency = currency
        self.excl_tax = excl_tax
        if incl_tax is not None:
            # Keep the supplied incl_tax so a memorized-incl path can
            # still look plausible; tax itself is still forced to 0.
            self.incl_tax = incl_tax
            self.is_tax_known = True
        elif tax is not None:
            # Intentional break: drop the supplied tax amount.
            self.incl_tax = excl_tax
            self.is_tax_known = True
        else:
            self.incl_tax = None
            self.is_tax_known = False

    def _get_tax(self):
        return Decimal("0")

    def _set_tax(self, value):
        self.incl_tax = self.excl_tax
        self.is_tax_known = True

    tax = property(_get_tax, _set_tax)

    def __repr__(self):
        if self.is_tax_known:
            return "%s(currency=%r, excl_tax=%r, incl_tax=%r, tax=%r)" % (
                self.__class__.__name__,
                self.currency,
                self.excl_tax,
                self.incl_tax,
                self.tax,
            )
        return "%s(currency=%r, excl_tax=%r)" % (
            self.__class__.__name__,
            self.currency,
            self.excl_tax,
        )

    def __eq__(self, other):
        return (
            self.currency == other.currency
            and self.excl_tax == other.excl_tax
            and self.incl_tax == other.incl_tax
        )
