# SPDX-License-Identifier: Apache-2.0
"""Known-bad: swallow the mixed-tax-rate NotImplementedError.

Patches ``SalePaymentLineProcessed.process`` after import. Does not
edit ``legacy/``. The 27-trace replay already records that mixed
rates must raise on ``payment_allocation_mixed_rate``.
"""
from __future__ import annotations

from decimal import Decimal as D

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from accounting.apps.books.calculators import SalePaymentLineProcessed

    def process(self):
        for line in self.sale.lines.all():
            tax_rate = line.tax_rate
            line_factor = line.line_price_incl_tax / self.sale.total_incl_tax
            portion_amount = self.payment.amount * line_factor
            portion_amount_excl_tax = portion_amount / (D("1") + tax_rate.rate)
            if self.tax_rate is None:
                self.tax_rate = tax_rate
            # Known-bad: keep allocating across mixed rates.
            self.amount_excl_tax += portion_amount_excl_tax

    SalePaymentLineProcessed.process = process
    _INSTALLED = True
