# SPDX-License-Identifier: Apache-2.0
"""Golden-independent invariants for the S1 Stage C gate.

These checks use live pin objects, not ``golden/expected.json``.
They are not a proof of accounting law. They catch memorized replay
and simple arithmetic breaks on the already-executed pure-Python APIs.

Invariants:
- excl + tax == incl when tax is known
- total_due_incl_tax == total_incl_tax - total_paid
- profits() == total_collected() - total_expenses()
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from hook import ensure_pin_path


@dataclass
class LiveBundle:
    prices: list[Any]
    sales: list[Any]
    calculators: list[Any]


def collect_live_bundle() -> LiveBundle:
    """Construct pin objects the 27-trace runner already exercises."""
    ensure_pin_path()
    from django.db.models import RelatedManager

    from accounting.apps.books.calculators import ProfitsLossCalculator
    from accounting.apps.books.models import Invoice, InvoiceLine, Organization, Payment, TaxRate
    from accounting.libs.prices import Price

    standard = TaxRate(pk=1, name="standard", rate=Decimal("0.20"))
    line = InvoiceLine(
        tax_rate=standard,
        unit_price_excl_tax=Decimal("50.00"),
        quantity=Decimal("1"),
        label="standard",
    )
    org = Organization(pk=1, display_name="Pin", legal_name="Pin")
    org.employees = RelatedManager()
    sale = Invoice(pk=12, number=12, organization=org)
    sale.lines = RelatedManager([line])
    sale.payments = RelatedManager([Payment(amount=Decimal("60.00"), date_paid=date(2024, 1, 15))])
    sale.compute_totals()

    org.invoices = RelatedManager([sale])
    org.bills = RelatedManager()

    prices = [
        Price("EUR", Decimal("10.00"), tax=Decimal("2.00")),
        Price("EUR", Decimal("10.00"), incl_tax=Decimal("12.00")),
        Price("EUR", Decimal("10.00"), tax=Decimal("0")),
    ]
    calculators = [
        ProfitsLossCalculator(org, start=date(2024, 1, 1), end=date(2024, 2, 28)),
        ProfitsLossCalculator(org),
    ]
    return LiveBundle(prices=prices, sales=[sale], calculators=calculators)


def evaluate_invariants(*, pin_executed: bool, live: LiveBundle | None) -> list[str]:
    """Return invariant failures. Empty means the live pin held.

    A golden-echo / memorized replay must set ``pin_executed=False``
    and ``live=None`` so this function fails even when JSON replay
    would have passed.
    """
    errors: list[str] = []
    if not pin_executed or live is None:
        errors.append(
            "INVARIANT FAILURE: pin not executed "
            "(golden echo / memorized expected.json)"
        )
        return errors

    for index, price in enumerate(live.prices):
        if not price.is_tax_known:
            continue
        if price.excl_tax + price.tax != price.incl_tax:
            errors.append(
                "INVARIANT FAILURE: excl+tax != incl "
                f"on live Price[{index}] "
                f"excl={price.excl_tax} tax={price.tax} incl={price.incl_tax}"
            )

    for index, sale in enumerate(live.sales):
        due = sale.total_incl_tax - sale.total_paid
        if sale.total_due_incl_tax != due:
            errors.append(
                "INVARIANT FAILURE: total_due_incl != incl - paid "
                f"on live sale[{index}] "
                f"due={sale.total_due_incl_tax} incl={sale.total_incl_tax} "
                f"paid={sale.total_paid}"
            )

    for index, calculator in enumerate(live.calculators):
        collected = calculator.total_collected()
        expenses = calculator.total_expenses()
        profits = calculator.profits()
        if profits != collected - expenses:
            errors.append(
                "INVARIANT FAILURE: profits != collected - expenses "
                f"on live calculator[{index}] "
                f"profits={profits} collected={collected} expenses={expenses}"
            )
    return errors


def check_live_invariants() -> list[str]:
    return evaluate_invariants(pin_executed=True, live=collect_live_bundle())


def check_golden_echo_invariants() -> list[str]:
    """Invariants against the echo probe: pin must not count as executed."""
    from probes import golden_echo

    if golden_echo.PIN_EXECUTED:
        return ["INVARIANT FAILURE: golden echo unexpectedly executed the pin"]
    # Replay payload is ignored on purpose. Consistent golden JSON is
    # not enough; the gate requires live pin objects.
    return evaluate_invariants(pin_executed=golden_echo.PIN_EXECUTED, live=None)
