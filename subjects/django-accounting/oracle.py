#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Golden-file oracle for the pinned django-accounting slice.

This runner replays recorded traces against
dulacp/django-accounting 2e61776a653e719a4c15578ab385603a6066c2b6.
A match is not a proof of accounting correctness. Django ORM and SQL
are not executed. See ORACLE.md next to this file.

Compare mode is the default. A Generator must not read
subjects/django-accounting/golden/.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

SUBJECT = Path(__file__).resolve().parent
STUBS = SUBJECT / "stubs"
LEGACY = SUBJECT / "legacy"
DEFAULT_GOLDEN = SUBJECT / "golden" / "expected.json"
PIN = (LEGACY / "PIN").read_text(encoding="utf-8").splitlines()
PIN_COMMIT = next(line.split("=", 1)[1] for line in PIN if line.startswith("commit="))
CLAIM = (
    "Replay of recorded traces from the pinned dulacp/django-accounting "
    "commit 2e61776a653e719a4c15578ab385603a6066c2b6. "
    "This is not a proof of accounting correctness. "
    "Django ORM and SQL are not executed; the stub is import-only."
)

for path in (STUBS, LEGACY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from django.db.models import RelatedManager  # noqa: E402

from accounting.apps.books.calculators import (  # noqa: E402
    ProfitsLossCalculator,
    SalePaymentLineProcessed,
)
from accounting.apps.books.models import (  # noqa: E402
    Bill,
    BillLine,
    Invoice,
    InvoiceLine,
    Organization,
    Payment,
    TaxRate,
)
from accounting.libs.intervals import TimeInterval  # noqa: E402
from accounting.libs.prices import Price  # noqa: E402


def dec(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return format(value, "f")


def exception_payload(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": str(exc)}


def tax_rate(pk: int, name: str, rate: str) -> TaxRate:
    return TaxRate(pk=pk, name=name, rate=Decimal(rate))


def invoice_line(tax: TaxRate, unit: str, quantity: str = "1") -> InvoiceLine:
    return InvoiceLine(tax_rate=tax, unit_price_excl_tax=Decimal(unit), quantity=Decimal(quantity), label=tax.name)


def bill_line(tax: TaxRate, unit: str, quantity: str = "1") -> BillLine:
    return BillLine(tax_rate=tax, unit_price_excl_tax=Decimal(unit), quantity=Decimal(quantity), label=tax.name)


def bind_sale(sale: Invoice | Bill, lines: list[Any], payments: list[Payment] | None = None) -> Invoice | Bill:
    sale.lines = RelatedManager(lines)
    sale.payments = RelatedManager(payments or [])
    sale.compute_totals()
    return sale


def price_payload(price: Price) -> dict[str, Any]:
    return {
        "currency": price.currency,
        "excl_tax": dec(price.excl_tax),
        "incl_tax": dec(price.incl_tax),
        "tax": dec(price.tax) if price.is_tax_known else None,
        "is_tax_known": price.is_tax_known,
        "repr": repr(price),
    }


def sale_payload(sale: Invoice | Bill) -> dict[str, Any]:
    return {
        "total_excl_tax": dec(sale.total_excl_tax),
        "total_incl_tax": dec(sale.total_incl_tax),
        "total_tax": dec(sale.total_tax),
        "computed_excl": dec(sale.get_total_excl_tax()),
        "computed_incl": dec(sale.get_total_incl_tax()),
        "total_paid": dec(sale.total_paid),
        "total_due_incl_tax": dec(sale.total_due_incl_tax),
        "is_fully_paid": sale.is_fully_paid(),
        "is_partially_paid": bool(sale.is_partially_paid()),
        "lines": [
            {
                "excl": dec(line.line_price_excl_tax),
                "incl": dec(line.line_price_incl_tax),
                "taxes": dec(line.taxes),
                "unit_excl": dec(line.unit_price.excl_tax),
                "unit_incl": dec(line.unit_price.incl_tax),
            }
            for line in sale.lines.all()
        ],
    }


def allocation_payload(sale: Invoice | Bill, amount: str, paid: date) -> dict[str, Any]:
    processed = SalePaymentLineProcessed(sale, Payment(amount=Decimal(amount), date_paid=paid))
    processed.process()
    return {
        "amount_excl_tax": dec(processed.amount_excl_tax),
        "tax_pk": processed.tax_rate.pk,
        "tax_rate": dec(processed.tax_rate.rate),
    }


def profits_payload(calculator: ProfitsLossCalculator) -> dict[str, Any]:
    return {
        "collected": dec(calculator.total_collected()),
        "expenses": dec(calculator.total_expenses()),
        "profits": dec(calculator.profits()),
        "period_start": calculator.period.start.isoformat() if calculator.period.start else None,
        "period_end": calculator.period.end.isoformat() if calculator.period.end else None,
    }


def run_cases() -> dict[str, Any]:
    standard = tax_rate(1, "standard", "0.20")
    reduced = tax_rate(2, "reduced", "0.05")
    zero = tax_rate(3, "zero", "0")

    org = Organization(pk=1, display_name="Pin", legal_name="Pin")
    other = Organization(pk=2, display_name="Other", legal_name="Other")
    empty = Organization(pk=4, display_name="Empty", legal_name="Empty")

    inv_multi = bind_sale(
        Invoice(pk=10, number=10, organization=org),
        [invoice_line(standard, "10.00", "2"), invoice_line(reduced, "4.00", "3")],
    )
    inv_zero = bind_sale(Invoice(pk=11, number=11, organization=org), [invoice_line(zero, "25.00", "1")])
    inv_paid = bind_sale(
        Invoice(pk=12, number=12, organization=org),
        [invoice_line(standard, "50.00", "1")],
        [Payment(amount=Decimal("60.00"), date_paid=date(2024, 1, 15))],
    )
    inv_partial = bind_sale(
        Invoice(pk=13, number=13, organization=org),
        [invoice_line(standard, "100.00", "1")],
        [Payment(amount=Decimal("40.00"), date_paid=date(2024, 2, 1))],
    )
    inv_quantize = bind_sale(
        Invoice(pk=14, number=14, organization=org),
        [invoice_line(standard, "10.00", "1")],
        [Payment(amount=Decimal("12.001"), date_paid=date(2024, 2, 2))],
    )
    inv_half = bind_sale(
        Invoice(pk=19, number=19, organization=org),
        [invoice_line(standard, "10.00", "0.50")],
    )
    inv_past_due = bind_sale(
        Invoice(pk=17, number=17, organization=org, date_dued=date(2020, 1, 1)),
        [invoice_line(standard, "10.00", "1")],
    )
    bill = bind_sale(
        Bill(pk=20, number=20, organization=org),
        [bill_line(standard, "20.00", "1")],
        [Payment(amount=Decimal("24.00"), date_paid=date(2024, 3, 1))],
    )
    outsider = bind_sale(
        Invoice(pk=99, number=99, organization=other),
        [invoice_line(standard, "1000.00", "1")],
        [Payment(amount=Decimal("1200.00"), date_paid=date(2024, 3, 1))],
    )
    dated = bind_sale(
        Invoice(pk=15, number=15, organization=org),
        [invoice_line(standard, "80.00", "1")],
        [
            Payment(amount=Decimal("30.00"), date_paid=date(2023, 12, 31)),
            Payment(amount=Decimal("66.00"), date_paid=date(2024, 1, 10)),
        ],
    )

    org.invoices = RelatedManager([inv_multi, inv_zero, inv_paid, inv_partial, inv_quantize, dated])
    org.bills = RelatedManager([bill])
    org.employees = RelatedManager(
        [
            type("Employee", (), {"salary_follows_profits": True, "shares_percentage": Decimal("0.50"), "payroll_tax_rate": Decimal("0.10")})(),
            type("Employee", (), {"salary_follows_profits": False, "shares_percentage": Decimal("0.50"), "payroll_tax_rate": Decimal("0.10")})(),
        ]
    )
    other.invoices = RelatedManager([outsider])
    other.bills = RelatedManager()
    empty.invoices = RelatedManager()
    empty.bills = RelatedManager()

    dated_only = Organization(pk=5, display_name="Dated", legal_name="Dated")
    dated_only.invoices = RelatedManager([dated])
    dated_only.bills = RelatedManager()

    mixed = bind_sale(
        Invoice(pk=16, number=16, organization=org),
        [invoice_line(standard, "10.00", "1"), invoice_line(reduced, "10.00", "1")],
        [Payment(amount=Decimal("10.00"), date_paid=date(2024, 1, 1))],
    )
    mixed_error: dict[str, str] | None = None
    try:
        SalePaymentLineProcessed(mixed, Payment(amount=Decimal("10.00"), date_paid=date(2024, 1, 1))).process()
    except NotImplementedError as exc:
        mixed_error = exception_payload(exc)

    unknown_tax_error: dict[str, str] | None = None
    try:
        _ = Price("USD", Decimal("10.00")).tax
    except TypeError as exc:
        unknown_tax_error = exception_payload(exc)

    interval_error: dict[str, str] | None = None
    try:
        TimeInterval("2024-01-01", None)
    except AssertionError as exc:
        interval_error = exception_payload(exc)

    sum_type_error: dict[str, str] | None = None
    try:
        ProfitsLossCalculator(org, sum_type="accurial")
    except AssertionError as exc:
        sum_type_error = exception_payload(exc)

    collected = ProfitsLossCalculator(org, start=date(2024, 1, 1), end=date(2024, 2, 28))
    year = ProfitsLossCalculator(org)
    dated_period = ProfitsLossCalculator(dated_only, start=date(2024, 1, 1), end=date(2024, 2, 28))
    dated_all = ProfitsLossCalculator(dated_only)

    price_tax = Price("EUR", Decimal("10.00"), tax=Decimal("2.00"))
    price_incl = Price("EUR", Decimal("10.00"), incl_tax=Decimal("12.00"))
    price_unknown = Price("USD", Decimal("10.00"))
    price_later = Price("USD", Decimal("10.00"))
    price_later.tax = Decimal("2.00")
    price_zero_tax = Price("EUR", Decimal("10.00"), tax=Decimal("0"))
    open_interval = TimeInterval(None, None)
    bounded_interval = TimeInterval(date(2024, 1, 1), date(2024, 2, 28))

    return {
        "claim": CLAIM,
        "pin": PIN_COMMIT,
        "cases": {
            "price_from_tax": price_payload(price_tax),
            "price_from_incl": price_payload(price_incl),
            "price_unknown": {
                "currency": price_unknown.currency,
                "excl_tax": dec(price_unknown.excl_tax),
                "incl_tax": dec(price_unknown.incl_tax),
                "is_tax_known": price_unknown.is_tax_known,
                "repr": repr(price_unknown),
            },
            "price_unknown_tax_access": unknown_tax_error,
            "price_set_later": price_payload(price_later),
            "price_tax_zero": price_payload(price_zero_tax),
            "price_equality": {
                "tax_vs_incl": price_tax == price_incl,
                "unknown_vs_tax": price_unknown == price_tax,
                "currency_matters": Price("USD", Decimal("10.00"), tax=Decimal("2.00")) == price_tax,
                "same_values": Price("EUR", Decimal("10.00"), tax=Decimal("2.00")) == price_tax,
            },
            "time_interval": {
                "open_start": open_interval.start,
                "open_end": open_interval.end,
                "bounded_start": bounded_interval.start.isoformat(),
                "bounded_end": bounded_interval.end.isoformat(),
                "bad_start": interval_error,
            },
            "invoice_multi_rate": sale_payload(inv_multi),
            "invoice_zero_rate": sale_payload(inv_zero),
            "invoice_fully_paid": sale_payload(inv_paid),
            "invoice_partial": sale_payload(inv_partial),
            "invoice_quantize_paid": sale_payload(inv_quantize),
            "invoice_half_quantity": sale_payload(inv_half),
            "invoice_past_due_unpaid": sale_payload(inv_past_due),
            "bill_standard": sale_payload(bill),
            "payment_allocation_single_rate": allocation_payload(inv_paid, "60.00", date(2024, 1, 15)),
            "payment_allocation_partial": allocation_payload(inv_partial, "40.00", date(2024, 2, 1)),
            "payment_allocation_zero_rate": allocation_payload(inv_zero, "25.00", date(2024, 1, 20)),
            "payment_allocation_mixed_rate": mixed_error,
            "profits_period_2024_jan_feb": profits_payload(collected),
            "profits_all_time": profits_payload(year),
            "profits_empty_organization": profits_payload(ProfitsLossCalculator(empty)),
            "profits_dated_invoice_only": {
                "jan_feb": profits_payload(dated_period),
                "all_time": profits_payload(dated_all),
            },
            "calculator_rejects_unknown_sum_type": sum_type_error,
            "payroll_on_partial": {"payroll_taxes": dec(inv_partial.payroll_taxes)},
            "outsider_excluded": {
                "other_collected": dec(ProfitsLossCalculator(other).total_collected()),
                "org_ignores_other": dec(year.total_collected()) != dec(ProfitsLossCalculator(other).total_collected()),
            },
        },
    }


def write_golden(payload: dict[str, Any], golden: Path) -> None:
    golden.parent.mkdir(parents=True, exist_ok=True)
    golden.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compare(payload: dict[str, Any], golden: Path) -> int:
    if not golden.is_file():
        print(f"ORACLE FAILURE: missing {golden}", file=sys.stderr)
        return 2
    expected = json.loads(golden.read_text(encoding="utf-8"))
    if payload == expected:
        print(f"ORACLE OK pin={PIN_COMMIT} cases={len(payload['cases'])} replay-only")
        return 0
    print(f"ORACLE FAILURE: computed output differs from {golden}", file=sys.stderr)
    got_cases = payload.get("cases", {})
    exp_cases = expected.get("cases", {})
    if payload.get("pin") != expected.get("pin"):
        print(f"  pin: computed {payload.get('pin')!r} expected {expected.get('pin')!r}", file=sys.stderr)
    if payload.get("claim") != expected.get("claim"):
        print(f"  claim: computed {payload.get('claim')!r} expected {expected.get('claim')!r}", file=sys.stderr)
    for name in sorted(set(got_cases) | set(exp_cases)):
        if got_cases.get(name) != exp_cases.get(name):
            print(f"  case {name}:", file=sys.stderr)
            print(f"    computed {json.dumps(got_cases.get(name), sort_keys=True)}", file=sys.stderr)
            print(f"    expected {json.dumps(exp_cases.get(name), sort_keys=True)}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay recorded django-accounting traces (not a correctness proof)")
    parser.add_argument("--write", action="store_true", help="rewrite the golden file from the pinned slice")
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN, help="golden file to compare or write")
    args = parser.parse_args()
    payload = run_cases()
    golden = args.golden
    if args.write:
        write_golden(payload, golden)
        print(f"WROTE {golden} pin={PIN_COMMIT} cases={len(payload['cases'])} replay-only")
        return 0
    return compare(payload, golden)


if __name__ == "__main__":
    raise SystemExit(main())
