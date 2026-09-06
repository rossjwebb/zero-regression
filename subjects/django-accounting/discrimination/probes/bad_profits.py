# SPDX-License-Identifier: Apache-2.0
"""Known-bad: drop the in-process payment period filter.

``QuerySet.filter`` is a no-op on the import-only stub, so the pin's
``ProfitsLossCalculator.process_generator`` re-checks ``date_paid``
in Python. This probe skips those continues. It does not edit
``legacy/``. The 27-trace replay already exercises the period window
on ``profits_period_2024_jan_feb``.
"""
from __future__ import annotations

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from accounting.apps.books.calculators import (
        ProfitsLossCalculator,
        SalePaymentLineProcessed,
    )

    def process_generator(self, sales_queryset):
        sales_queryset = sales_queryset.filter(organization=self.organization)
        sales_queryset = sales_queryset.prefetch_related(
            "lines",
            "lines__tax_rate",
            "payments",
        ).distinct()
        for sale in sales_queryset:
            for pay in sale.payments.all():
                output = SalePaymentLineProcessed(sale, pay)
                output.process()
                yield output

    ProfitsLossCalculator.process_generator = process_generator
    _INSTALLED = True
