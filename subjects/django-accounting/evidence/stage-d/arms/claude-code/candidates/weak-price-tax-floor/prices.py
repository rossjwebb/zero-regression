# SPDX-License-Identifier: Apache-2.0
"""Stage D Claude Code arm candidate: intentional weak tax floor.

Claude · Max raw design floored ``incl_tax`` at ``excl_tax`` when tax
is set via the constructor or the tax setter, so negative tax cannot
pull inclusive below exclusive. This pin-API adaptation keeps that
weak intent and uses ``incl_tax=None`` when tax is unknown (gemini
faithful-price-round shape). Other paths stay behaviour-preserving.

Applied via the Stage D import hook. Does not edit legacy/. Not paper S1.
"""
from __future__ import annotations


class Price(object):
    """Weak rewrite: negative tax cannot pull incl_tax below excl_tax."""

    def __init__(self, currency, excl_tax, incl_tax=None, tax=None):
        self.currency = currency
        self.excl_tax = excl_tax
        self._incl_tax = None
        self._tax_known = False
        if incl_tax is not None:
            self._incl_tax = incl_tax
            self._tax_known = True
        elif tax is not None:
            # Max weak intent: floor so negative tax cannot pull incl below excl.
            self._incl_tax = max(excl_tax, excl_tax + tax)
            self._tax_known = True

    @property
    def is_tax_known(self):
        return self._tax_known

    @is_tax_known.setter
    def is_tax_known(self, value):
        self._tax_known = bool(value)

    @property
    def incl_tax(self):
        return self._incl_tax

    @incl_tax.setter
    def incl_tax(self, value):
        self._incl_tax = value

    def _get_tax(self):
        return self._incl_tax - self.excl_tax

    def _set_tax(self, value):
        # Max weak intent: same floor as the tax= constructor path.
        self._incl_tax = max(self.excl_tax, self.excl_tax + value)
        self._tax_known = True

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
