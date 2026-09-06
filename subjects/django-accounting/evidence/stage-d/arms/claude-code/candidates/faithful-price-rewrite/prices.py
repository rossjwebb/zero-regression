# SPDX-License-Identifier: Apache-2.0
"""Stage D Claude Code arm candidate: faithful Price rewrite (pin API).

Claude · Max raw design used the pin constructor but omitted
``incl_tax=None`` when tax is unknown (AttributeError) and added
operators the pin does not have. This file is the pin-API adaptation
of that faithful intent: same public arithmetic as the pin, private
tax-known storage (gemini faithful-price-round shape).

Applied via the Stage D import hook. Does not edit legacy/.
Not the pin. Not paper S1.
"""
from __future__ import annotations


class Price(object):
    """Faithful rewrite of pin Price with the same public arithmetic."""

    def __init__(self, currency, excl_tax, incl_tax=None, tax=None):
        self.currency = currency
        self.excl_tax = excl_tax
        self._incl_tax = None
        self._tax_known = False
        if incl_tax is not None:
            self._incl_tax = incl_tax
            self._tax_known = True
        elif tax is not None:
            self._incl_tax = excl_tax + tax
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
        # Pin raises TypeError when incl_tax is None (None - Decimal).
        return self._incl_tax - self.excl_tax

    def _set_tax(self, value):
        self._incl_tax = self.excl_tax + value
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
