# SPDX-License-Identifier: Apache-2.0
"""Scaffold models that attach the pin's QuerySet classes.

The pin's ``Organization`` / ``Invoice`` / ``Bill`` / ``Payment``
classes in ``legacy/accounting/apps/books/models.py`` are not imported.
That module needs Django 1.7-era APIs (``django.core.urlresolvers``,
``SortedDict``, ``ForeignKey`` without ``on_delete``, ``people.Client``)
that do not load on Django 5.2 + Python 3.12.3.

These tables exist so ``InvoiceQuerySet.turnover_*`` /
``BillQuerySet.debts_*`` / ``dued`` / ``total_paid`` from the pin's
``managers.py`` can issue real ``QuerySet.aggregate(Sum(...))`` SQL.

``Payment`` is a plain FK (``related_name="payments"``), not the pin's
``GenericRelation``. The lookup ``payments__amount`` is the same shape
the pin's ``TotalQuerySetMixin.total_paid`` uses.

Do not edit ``legacy/``.
"""
from __future__ import annotations

from decimal import Decimal as D

from django.db import models

from accounting.apps.books.managers import BillQuerySet, InvoiceQuerySet


class Organization(models.Model):
    display_name = models.CharField(max_length=150)
    legal_name = models.CharField(max_length=150)

    class Meta:
        app_label = "s1_org_aggregates"

    def __str__(self) -> str:
        return self.legal_name

    @property
    def turnover_excl_tax(self):
        return self.invoices.turnover_excl_tax() or D("0.00")

    @property
    def turnover_incl_tax(self):
        return self.invoices.turnover_incl_tax() or D("0.00")

    @property
    def debts_excl_tax(self):
        return self.bills.debts_excl_tax() or D("0.00")

    @property
    def debts_incl_tax(self):
        return self.bills.debts_incl_tax() or D("0.00")

    @property
    def profits(self):
        return self.turnover_excl_tax - self.debts_excl_tax

    @property
    def overdue_total(self):
        # Pin formula: due invoices' incl turnover minus their payments.
        # Django SUM of no rows is NULL; coalesce so overdue_total is usable.
        due_invoices = self.invoices.dued()
        due_turnover = due_invoices.turnover_incl_tax() or D("0.00")
        total_paid = due_invoices.total_paid() or D("0.00")
        return due_turnover - total_paid


class Invoice(models.Model):
    organization = models.ForeignKey(
        Organization, related_name="invoices", on_delete=models.CASCADE
    )
    number = models.IntegerField()
    total_excl_tax = models.DecimalField(max_digits=12, decimal_places=2, default=D("0"))
    total_incl_tax = models.DecimalField(max_digits=12, decimal_places=2, default=D("0"))
    date_dued = models.DateField(blank=True, null=True)
    objects = InvoiceQuerySet.as_manager()

    class Meta:
        app_label = "s1_org_aggregates"


class Bill(models.Model):
    organization = models.ForeignKey(
        Organization, related_name="bills", on_delete=models.CASCADE
    )
    number = models.IntegerField()
    total_excl_tax = models.DecimalField(max_digits=12, decimal_places=2, default=D("0"))
    total_incl_tax = models.DecimalField(max_digits=12, decimal_places=2, default=D("0"))
    date_dued = models.DateField(blank=True, null=True)
    objects = BillQuerySet.as_manager()

    class Meta:
        app_label = "s1_org_aggregates"


class Payment(models.Model):
    invoice = models.ForeignKey(
        Invoice, related_name="payments", on_delete=models.CASCADE, null=True, blank=True
    )
    bill = models.ForeignKey(
        Bill, related_name="payments", on_delete=models.CASCADE, null=True, blank=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        app_label = "s1_org_aggregates"
