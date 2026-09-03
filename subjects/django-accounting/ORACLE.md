# Oracle claim

`oracle.py` replays a recorded set of traces against the frozen
`dulacp/django-accounting` tree at

`2e61776a653e719a4c15578ab385603a6066c2b6` (2 December 2017, MIT).

A match against `golden/expected.json` means those same calls still
produce the same JSON. It is **not** a proof that the pin does
accounting correctly. It does not certify tax law, double-entry
invariants, or collected-versus-accrual profits.

## What is executed

- `accounting.libs.prices.Price` (pure Python on the pin)
- In-memory sale-line totals and payment totals on the pin's
  `AbstractSale` / `AbstractSaleLine` methods, iterating collections
  bound by the runner
- `SalePaymentLineProcessed.process` on the pin
- `ProfitsLossCalculator` Python loops on the pin, including the
  in-process date checks on each payment

## What is not executed

Django ORM and SQL are not executed. The stub under `stubs/` is an
import shim for Django 1.7-era names. `QuerySet.filter` does not apply
lookups. There is no `aggregate`, so organisation-level
`turnover_*` / `debts_*` / `overdue_total` paths (which call
`QuerySet.aggregate(Sum(...))` in the pin's managers) are not in the
golden file.

This file is the claim. The golden file repeats it in the `claim`
field. S1 is not a paper execution until this pull request is merged
and the paper says so.
