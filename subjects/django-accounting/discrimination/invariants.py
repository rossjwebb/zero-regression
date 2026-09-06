# SPDX-License-Identifier: Apache-2.0
"""Golden-independent invariants for the S1 Stage C gate.

These checks use live pin objects, not ``golden/expected.json``.
They are not a proof of accounting law. They catch memorized replay
and simple arithmetic breaks on the already-executed pure-Python APIs.

Invariants:
- excl + tax == incl when tax is known
- total_due_incl_tax == total_incl_tax - total_paid
- profits() == total_collected() - total_expenses()
  (exercised on a live org where expenses > collected, because the
  27-trace golden has no negative-profit case)
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
    """Construct live pin objects, including a loss-making org.

    The profitable sale matches a 27-trace fixture. The expenses>
    collected org is golden-independent: replay cannot see it.
    """
    ensure_pin_path()
    from django.db.models import RelatedManager

    from accounting.apps.books.calculators import ProfitsLossCalculator
    from accounting.apps.books.models import (
        Bill,
        BillLine,
        Invoice,
        InvoiceLine,
        Organization,
        Payment,
        TaxRate,
    )
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

    # Loss-making org: not in the 27-trace golden. Expenses exceed
    # collected so a clamp-to-zero profits() diverges from pin
    # arithmetic without widening expected.json.
    loss_sale_line = InvoiceLine(
        tax_rate=standard,
        unit_price_excl_tax=Decimal("10.00"),
        quantity=Decimal("1"),
        label="standard",
    )
    loss_bill_line = BillLine(
        tax_rate=standard,
        unit_price_excl_tax=Decimal("40.00"),
        quantity=Decimal("1"),
        label="standard",
    )
    loss_org = Organization(pk=3, display_name="Loss", legal_name="Loss")
    loss_org.employees = RelatedManager()
    loss_sale = Invoice(pk=30, number=30, organization=loss_org)
    loss_sale.lines = RelatedManager([loss_sale_line])
    loss_sale.payments = RelatedManager(
        [Payment(amount=Decimal("12.00"), date_paid=date(2024, 1, 15))]
    )
    loss_sale.compute_totals()
    loss_bill = Bill(pk=31, number=31, organization=loss_org)
    loss_bill.lines = RelatedManager([loss_bill_line])
    loss_bill.payments = RelatedManager(
        [Payment(amount=Decimal("48.00"), date_paid=date(2024, 1, 20))]
    )
    loss_bill.compute_totals()
    loss_org.invoices = RelatedManager([loss_sale])
    loss_org.bills = RelatedManager([loss_bill])

    prices = [
        Price("EUR", Decimal("10.00"), tax=Decimal("2.00")),
        Price("EUR", Decimal("10.00"), incl_tax=Decimal("12.00")),
        Price("EUR", Decimal("10.00"), tax=Decimal("0")),
    ]
    calculators = [
        ProfitsLossCalculator(org, start=date(2024, 1, 1), end=date(2024, 2, 28)),
        ProfitsLossCalculator(org),
        ProfitsLossCalculator(loss_org),
        ProfitsLossCalculator(loss_org, start=date(2024, 1, 1), end=date(2024, 2, 28)),
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

    saw_negative_pin_arithmetic = False
    for index, calculator in enumerate(live.calculators):
        collected = calculator.total_collected()
        expenses = calculator.total_expenses()
        profits = calculator.profits()
        pin_net = collected - expenses
        if pin_net < 0:
            saw_negative_pin_arithmetic = True
            if profits >= 0:
                errors.append(
                    "INVARIANT FAILURE: profits cannot go negative "
                    "while collected - expenses is negative "
                    f"on live calculator[{index}] "
                    f"profits={profits} collected={collected} expenses={expenses}"
                )
        if profits != pin_net:
            errors.append(
                "INVARIANT FAILURE: profits != collected - expenses "
                f"on live calculator[{index}] "
                f"profits={profits} collected={collected} expenses={expenses}"
            )
    if not saw_negative_pin_arithmetic:
        errors.append(
            "INVARIANT FAILURE: live bundle has no expenses>collected "
            "fixture; clamp-to-zero profits() would be invisible "
            "under the 27-trace golden"
        )
    return errors


def check_live_invariants() -> list[str]:
    return evaluate_invariants(pin_executed=True, live=collect_live_bundle())


def check_clamp_to_zero_rejected() -> list[str]:
    """Yardstick-local: clamp-to-zero profits() must fail live invariants.

    The 27-trace golden has no negative-profit case, so a
    ``max(0, collected - expenses)`` rewrite still matches
    ``expected.json``. This check does not read the golden file and
    does not edit ``legacy/``. Empty return means the yardstick
    rejected the clamp. A non-empty list means the gap is still open.
    """
    from accounting.apps.books.calculators import ProfitsLossCalculator

    original = ProfitsLossCalculator.profits

    def clamped(self):
        net = original(self)
        if net < Decimal("0"):
            return Decimal("0")
        return net

    ProfitsLossCalculator.profits = clamped
    try:
        failures = check_live_invariants()
    finally:
        ProfitsLossCalculator.profits = original

    if not failures:
        return [
            "INVARIANT FAILURE: clamp-to-zero profits() was not rejected "
            "(live bundle missing expenses>collected fixture?)"
        ]
    named = any(
        "cannot go negative" in item or "profits != collected - expenses" in item
        for item in failures
    )
    if not named:
        return [
            "INVARIANT FAILURE: clamp-to-zero failed invariants for an "
            f"unexpected reason: {failures}"
        ]
    return []


def check_golden_echo_invariants() -> list[str]:
    """Invariants against the echo probe: pin must not count as executed."""
    from probes import golden_echo

    if golden_echo.PIN_EXECUTED:
        return ["INVARIANT FAILURE: golden echo unexpectedly executed the pin"]
    # Replay payload is ignored on purpose. Consistent golden JSON is
    # not enough; the gate requires live pin objects.
    return evaluate_invariants(pin_executed=golden_echo.PIN_EXECUTED, live=None)
