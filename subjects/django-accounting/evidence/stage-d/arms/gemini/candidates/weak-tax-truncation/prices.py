# SPDX-License-Identifier: Apache-2.0
"""Stage D Gemini arm candidate: intentional weak tax truncation.

Gemini raw design truncated tax with ROUND_DOWN on a made-up Price API.
This CoS pin-API adaptation floors tax via ROUND_DOWN on get/set, and
when tax is supplied at construction floors it before building incl_tax.
Also floors the tax *property* independently so excl+tax can disagree
with stored incl_tax (Gemini truncation spirit).

Applied via the Stage D import hook. Does not edit legacy/. Not paper S1.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN


def _floor_cent(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_DOWN)


class Price(object):
    """Weak rewrite: tax is truncated with ROUND_DOWN."""

    def __init__(self, currency, excl_tax, incl_tax=None, tax=None):
        self.currency = currency
        self.excl_tax = excl_tax
        if incl_tax is not None:
            # Keep supplied incl, but tax property will floor the delta.
            self.incl_tax = incl_tax
            self.is_tax_known = True
        elif tax is not None:
            self.incl_tax = excl_tax + _floor_cent(tax)
            self.is_tax_known = True
        else:
            self.incl_tax = None
            self.is_tax_known = False

    def _get_tax(self):
        # Intentional break: floor the delta; can disagree with incl-excl
        # when incl carried extra sub-cent precision from callers.
        raw = self.incl_tax - self.excl_tax
        floored = _floor_cent(raw)
        # Extra Gemini-style truncation: chop one cent from positive tax
        # so whole-cent golden taxes also diverge (ROUND_DOWN alone is a
        # no-op on exact 0.01 values already in the golden set).
        if floored > Decimal("0.00"):
            return floored - Decimal("0.01")
        return floored

    def _set_tax(self, value):
        self.incl_tax = self.excl_tax + _floor_cent(value)
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
