# SPDX-License-Identifier: Apache-2.0
"""Stage D Cursor candidate: intentional weak profits rewrite.

Rewrites ``ProfitsLossCalculator`` and drops the in-process
``date_paid`` window. ``QuerySet.filter`` is a no-op on the
import-only stub, so the pin re-checks dates in Python. This rewrite
keeps the queryset calls and skips those continues.

Applied via the Stage D import hook. Does not edit legacy/.
``SalePaymentLineProcessed`` stays on the pin. Not paper S1.
"""
from __future__ import annotations

from decimal import Decimal as D

from accounting.apps.books.calculators import SalePaymentLineProcessed
from accounting.libs.intervals import TimeInterval


class ProfitsLossCalculator(object):
    """Weak rewrite: period window is not applied to payments."""

    SUM_TYPE_COLLECTED = "collected"
    SUM_TYPE_CHOICES = (SUM_TYPE_COLLECTED,)

    organization = None

    def __init__(self, organization, sum_type=SUM_TYPE_COLLECTED, start=None, end=None):
        assert sum_type in self.SUM_TYPE_CHOICES, "Not a supported sum type"
        self.organization = organization
        self.period = TimeInterval(start=start, end=end)

    def process_generator(self, sales_queryset):
        sales_queryset = sales_queryset.filter(organization=self.organization)
        if self.period.start:
            sales_queryset = sales_queryset.filter(payments__date_paid__gte=self.period.start)
        if self.period.end:
            sales_queryset = sales_queryset.filter(payments__date_paid__lte=self.period.end)
        sales_queryset = sales_queryset.prefetch_related(
            "lines",
            "lines__tax_rate",
            "payments",
        ).distinct()

        for sale in sales_queryset:
            for pay in sale.payments.all():
                # Intentional break: do not re-check pay.date_paid
                # against self.period. The stub queryset filter is a
                # no-op, so out-of-window payments are counted.
                output = SalePaymentLineProcessed(sale, pay)
                output.process()
                yield output

    def total_collected(self):
        collected = D("0")
        for output in self.process_generator(self.organization.invoices.all()):
            collected += output.amount_excl_tax
        return collected

    def total_expenses(self):
        expenses = D("0")
        for output in self.process_generator(self.organization.bills.all()):
            expenses += output.amount_excl_tax
        return expenses

    def profits(self):
        return self.total_collected() - self.total_expenses()
