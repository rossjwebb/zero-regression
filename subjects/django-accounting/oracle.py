#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Golden-file oracle for the pinned django-accounting pricing slice.

Runs the legacy Price object, sale-line totals, payment allocation, and
collected-profits calculator through a Django stub. Compare mode is the
default. Generators must not read subjects/django-accounting/golden/.
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
from accounting.libs.prices import Price  # noqa: E402


def dec(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return format(value, "f")


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


def run_cases() -> dict[str, Any]:
    standard = tax_rate(1, "standard", "0.20")
    reduced = tax_rate(2, "reduced", "0.05")
    zero = tax_rate(3, "zero", "0")

    org = Organization(pk=1, display_name="Pin", legal_name="Pin")
    other = Organization(pk=2, display_name="Other", legal_name="Other")

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

    mixed = bind_sale(
        Invoice(pk=16, number=16, organization=org),
        [invoice_line(standard, "10.00", "1"), invoice_line(reduced, "10.00", "1")],
        [Payment(amount=Decimal("10.00"), date_paid=date(2024, 1, 1))],
    )
    mixed_error: str | None = None
    try:
        SalePaymentLineProcessed(mixed, Payment(amount=Decimal("10.00"), date_paid=date(2024, 1, 1))).process()
    except NotImplementedError as exc:
        mixed_error = str(exc)

    single_alloc = SalePaymentLineProcessed(inv_paid, Payment(amount=Decimal("60.00"), date_paid=date(2024, 1, 15)))
    single_alloc.process()

    collected = ProfitsLossCalculator(org, start=date(2024, 1, 1), end=date(2024, 2, 28))
    year = ProfitsLossCalculator(org)

    price_tax = Price("EUR", Decimal("10.00"), tax=Decimal("2.00"))
    price_incl = Price("EUR", Decimal("10.00"), incl_tax=Decimal("12.00"))
    price_unknown = Price("USD", Decimal("10.00"))
    price_later = Price("USD", Decimal("10.00"))
    price_later.tax = Decimal("2.00")

    due_invoice = bind_sale(
        Invoice(pk=17, number=17, organization=org, date_dued=date(2020, 1, 1)),
        [invoice_line(standard, "10.00", "1")],
    )
    current_invoice = bind_sale(
        Invoice(pk=18, number=18, organization=org, date_dued=date(2099, 1, 1)),
        [invoice_line(standard, "30.00", "1")],
    )
    org_overdue = Organization(pk=3, display_name="Due", legal_name="Due")
    org_overdue.invoices = RelatedManager([due_invoice, current_invoice])
    org_overdue.bills = RelatedManager()

    return {
        "pin": PIN_COMMIT,
        "cases": {
            "price_from_tax": price_payload(price_tax),
            "price_from_incl": price_payload(price_incl),
            "price_unknown": price_payload(price_unknown),
            "price_set_later": price_payload(price_later),
            "price_equality": {
                "tax_vs_incl": price_tax == price_incl,
                "unknown_vs_tax": price_unknown == price_tax,
                "currency_matters": Price("USD", Decimal("10.00"), tax=Decimal("2.00")) == price_tax,
            },
            "invoice_multi_rate": sale_payload(inv_multi),
            "invoice_zero_rate": sale_payload(inv_zero),
            "invoice_fully_paid": sale_payload(inv_paid),
            "invoice_partial": sale_payload(inv_partial),
            "invoice_quantize_paid": sale_payload(inv_quantize),
            "bill_standard": sale_payload(bill),
            "payment_allocation_single_rate": {
                "amount_excl_tax": dec(single_alloc.amount_excl_tax),
                "tax_pk": single_alloc.tax_rate.pk,
            },
            "payment_allocation_mixed_rate": {"error": mixed_error},
            "profits_period_2024_jan_feb": {
                "collected": dec(collected.total_collected()),
                "expenses": dec(collected.total_expenses()),
                "profits": dec(collected.profits()),
            },
            "profits_all_time": {
                "collected": dec(year.total_collected()),
                "expenses": dec(year.total_expenses()),
                "profits": dec(year.profits()),
            },
            "organization_derived": {
                "turnover_excl_tax": dec(org.turnover_excl_tax),
                "turnover_incl_tax": dec(org.turnover_incl_tax),
                "debts_excl_tax": dec(org.debts_excl_tax),
                "debts_incl_tax": dec(org.debts_incl_tax),
                "profits": dec(org.profits),
                "collected_tax": dec(org.collected_tax),
                "deductible_tax": dec(org.deductible_tax),
                "tax_provisionning": dec(org.tax_provisionning),
            },
            "payroll_on_partial": {"payroll_taxes": dec(inv_partial.payroll_taxes)},
            "overdue_total": {"overdue_total": dec(org_overdue.overdue_total)},
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
        print(f"ORACLE OK pin={PIN_COMMIT} cases={len(payload['cases'])}")
        return 0
    print(f"ORACLE FAILURE: computed output differs from {golden}", file=sys.stderr)
    got_cases = payload.get("cases", {})
    exp_cases = expected.get("cases", {})
    if payload.get("pin") != expected.get("pin"):
        print(f"  pin: computed {payload.get('pin')!r} expected {expected.get('pin')!r}", file=sys.stderr)
    for name in sorted(set(got_cases) | set(exp_cases)):
        if got_cases.get(name) != exp_cases.get(name):
            print(f"  case {name}:", file=sys.stderr)
            print(f"    computed {json.dumps(got_cases.get(name), sort_keys=True)}", file=sys.stderr)
            print(f"    expected {json.dumps(exp_cases.get(name), sort_keys=True)}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the django-accounting golden-file oracle")
    parser.add_argument("--write", action="store_true", help="rewrite the golden file from the pinned slice")
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN, help="golden file to compare or write")
    args = parser.parse_args()
    payload = run_cases()
    golden = args.golden
    if args.write:
        write_golden(payload, golden)
        print(f"WROTE {golden} pin={PIN_COMMIT} cases={len(payload['cases'])}")
        return 0
    return compare(payload, golden)


if __name__ == "__main__":
    raise SystemExit(main())
