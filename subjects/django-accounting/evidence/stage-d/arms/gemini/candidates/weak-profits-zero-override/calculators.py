# SPDX-License-Identifier: Apache-2.0
"""Stage D Gemini arm candidate: intentional weak profits clamp.

Gemini raw design forced negative net to zero on a made-up calculator
API (and had a syntax error). This CoS pin-API adaptation keeps the pin
period window and clamps ``profits()`` so a loss becomes zero.

Applied via the Stage D import hook. Does not edit legacy/.
SalePaymentLineProcessed stays on the pin. Not paper S1.
"""
from __future__ import annotations

from decimal import Decimal as D

from accounting.apps.books.calculators import SalePaymentLineProcessed
from accounting.libs.intervals import TimeInterval


class ProfitsLossCalculator(object):
    """Weak rewrite: never report a negative profit."""

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
                if self.period.start and pay.date_paid < self.period.start:
                    continue
                if self.period.end and pay.date_paid > self.period.end:
                    continue
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
        net = self.total_collected() - self.total_expenses()
        # Gemini weak intent: drop negative outcomes to zero.
        if net < D("0"):
            return D("0")
        return net
