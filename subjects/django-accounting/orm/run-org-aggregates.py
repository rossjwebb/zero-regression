#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Execute org-level aggregates through the pin's QuerySet classes.

Uses real Django 5.2.17 + SQLite. Does not import the pin's models.py.
Does not edit legacy/ or golden/. Does not print a mutation score.
This is not paper S1.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ORM = Path(__file__).resolve().parent
if str(ORM) not in sys.path:
    sys.path.insert(0, str(ORM))

from bootstrap import DJANGO_VERSION, PIN, probe_pin_models, setup  # noqa: E402

OK = (
    f"S1 ORM OK pin={PIN} django={DJANGO_VERSION} "
    "path=pin-managers-queryset-aggregate "
    "paper_s1=unexecuted mutation_score=not-stored"
)


def dec(value: object) -> str:
    if value is None:
        return "0.00"
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return format(value.quantize(Decimal("0.01")), "f")


def seed(models: dict) -> dict:
    Organization = models["Organization"]
    Invoice = models["Invoice"]
    Bill = models["Bill"]
    Payment = models["Payment"]

    org = Organization.objects.create(display_name="Pin", legal_name="Pin")
    other = Organization.objects.create(display_name="Other", legal_name="Other")
    empty = Organization.objects.create(display_name="Empty", legal_name="Empty")

    # Totals match the in-memory sales the replay oracle already binds
    # onto org / other. overdue adds inv_past_due, which the 27-trace
    # golden does not include (that case needs SQL).
    Invoice.objects.create(
        organization=org, number=10, total_excl_tax="32.00", total_incl_tax="36.60"
    )
    Invoice.objects.create(
        organization=org, number=11, total_excl_tax="25.00", total_incl_tax="25.00"
    )
    paid = Invoice.objects.create(
        organization=org, number=12, total_excl_tax="50.00", total_incl_tax="60.00"
    )
    Payment.objects.create(invoice=paid, amount="60.00")
    partial = Invoice.objects.create(
        organization=org, number=13, total_excl_tax="100.00", total_incl_tax="120.00"
    )
    Payment.objects.create(invoice=partial, amount="40.00")
    Invoice.objects.create(
        organization=org, number=14, total_excl_tax="10.00", total_incl_tax="12.00"
    )
    dated = Invoice.objects.create(
        organization=org, number=15, total_excl_tax="80.00", total_incl_tax="96.00"
    )
    Payment.objects.create(invoice=dated, amount="30.00")
    Payment.objects.create(invoice=dated, amount="66.00")
    Invoice.objects.create(
        organization=org,
        number=17,
        total_excl_tax="10.00",
        total_incl_tax="12.00",
        date_dued=date(2020, 1, 1),
    )
    bill = Bill.objects.create(
        organization=org, number=20, total_excl_tax="20.00", total_incl_tax="24.00"
    )
    Payment.objects.create(bill=bill, amount="24.00")
    Invoice.objects.create(
        organization=other, number=99, total_excl_tax="1000.00", total_incl_tax="1200.00"
    )
    return {"org": org, "other": other, "empty": empty}


def run() -> dict:
    models = setup()
    from django.db.models import QuerySet
    from django.test.utils import CaptureQueriesContext

    from accounting.apps.books.managers import InvoiceQuerySet

    seeded = seed(models)
    org = seeded["org"]
    other = seeded["other"]
    empty = seeded["empty"]
    connection = models["connection"]

    qs = org.invoices.all()
    if type(qs) is not InvoiceQuerySet:
        raise RuntimeError(f"S1 ORM FAIL-CLOSED: expected InvoiceQuerySet got {type(qs)}")
    if not issubclass(type(qs), QuerySet):
        raise RuntimeError("S1 ORM FAIL-CLOSED: InvoiceQuerySet is not a Django QuerySet")

    sql: list[str] = []
    with CaptureQueriesContext(connection) as captured:
        results = {
            "org_turnover_excl_tax": dec(org.turnover_excl_tax),
            "org_turnover_incl_tax": dec(org.turnover_incl_tax),
            "org_debts_excl_tax": dec(org.debts_excl_tax),
            "org_debts_incl_tax": dec(org.debts_incl_tax),
            "org_profits": dec(org.profits),
            "org_overdue_total": dec(org.overdue_total),
            "empty_turnover_excl_tax": dec(empty.turnover_excl_tax),
            "other_turnover_excl_tax": dec(other.turnover_excl_tax),
        }
    for item in captured.captured_queries:
        sql.append(item["sql"])

    if not sql:
        raise RuntimeError("S1 ORM FAIL-CLOSED: no SQL was issued")
    if not any("SUM(" in statement.upper() for statement in sql):
        raise RuntimeError("S1 ORM FAIL-CLOSED: captured SQL has no SUM(); this is not aggregate")
    if not any("date_dued" in statement for statement in sql):
        raise RuntimeError("S1 ORM FAIL-CLOSED: overdue path did not filter date_dued in SQL")

    # Isolation: other org's 1000 must not land in org turnover.
    if results["org_turnover_excl_tax"] != "307.00":
        raise RuntimeError(
            f"S1 ORM FAIL-CLOSED: unexpected org turnover_excl {results['org_turnover_excl_tax']!r}"
        )
    if results["other_turnover_excl_tax"] != "1000.00":
        raise RuntimeError(
            f"S1 ORM FAIL-CLOSED: unexpected other turnover_excl {results['other_turnover_excl_tax']!r}"
        )
    if results["empty_turnover_excl_tax"] != "0.00":
        raise RuntimeError("S1 ORM FAIL-CLOSED: empty organisation must coalesce SUM NULL to 0.00")
    if results["org_overdue_total"] != "12.00":
        raise RuntimeError(
            f"S1 ORM FAIL-CLOSED: unexpected overdue_total {results['org_overdue_total']!r}"
        )

    pin_models = probe_pin_models()
    if pin_models.get("imported") != "false":
        raise RuntimeError("S1 ORM FAIL-CLOSED: pin models.py unexpectedly imported")
    if "urlresolvers" not in pin_models.get("blocked", ""):
        raise RuntimeError(
            "S1 ORM FAIL-CLOSED: expected pin models.py to fail on urlresolvers; "
            f"got {pin_models}"
        )

    return {
        "kind": "s1-django-accounting-orm-receipt",
        "paper_s1": "unexecuted",
        "mutation_score": "not-stored",
        "pin": PIN,
        "django": DJANGO_VERSION,
        "path": "pin-managers-queryset-aggregate",
        "orm_sql_executed": True,
        "stub_used": False,
        "legacy_edited": False,
        "golden_widened": False,
        "pin_models_imported": False,
        "pin_models_blocked": pin_models["blocked"],
        "queryset_class": f"{type(qs).__module__}.{type(qs).__name__}",
        "sql_statements": len(sql),
        "sql": sql,
        "results": results,
        "claims": {
            "paper_s1": "unexecuted",
            "mutation_score": "not-stored",
            "orm_sql_executed": True,
            "path": "pin-managers-queryset-aggregate",
        },
    }


def main() -> int:
    try:
        receipt = run()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(OK)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
