# Oracle claim

`oracle.py` replays a recorded set of traces against the frozen
`dulacp/django-accounting` tree at

`2e61776a653e719a4c15578ab385603a6066c2b6` (2 December 2017, MIT).

A match against `golden/expected.json` means those same calls still
produce the same JSON. Stage C adds a discrimination gate
(`check-discrimination.py`): the yardstick is **replay + rejects known-bad probes**. A golden echo stub that returns the golden file
without calling the pin can still print the replay OK line; the
invariant gate must reject it.

This is not a proof of accounting correctness. It does not certify
tax law, double-entry invariants, or collected-versus-accrual
profits. It is not paper S1.

## What is executed

- `accounting.libs.prices.Price` (pure Python on the pin)
- In-memory sale-line totals and payment totals on the pin's
  `AbstractSale` / `AbstractSaleLine` methods, iterating collections
  bound by the runner
- `SalePaymentLineProcessed.process` on the pin
- `ProfitsLossCalculator` Python loops on the pin, including the
  in-process date checks on each payment

Known-bad probes patch those same callables through an import hook.
They do not edit `legacy/`. They do not add Django ORM or SQL.

Golden-independent invariants (live pin objects, not the golden
file):

- `excl + tax == incl` when tax is known
- `total_due_incl_tax == total_incl_tax - total_paid`
- `profits() == total_collected() - total_expenses()`

Those are arithmetic consistency checks. They are not accounting-law
certification.

## What is not executed

Django ORM and SQL are not executed by this oracle. The stub under
`stubs/` is an import shim for Django 1.7-era names. `QuerySet.filter`
does not apply lookups. There is no `aggregate` on the stub, so the
27-trace golden file still omits organisation-level `turnover_*` /
`debts_*` / `overdue_total`. A separate org-level scaffold
(`orm/run-org-aggregates.py`, Django 5.2.17 pin) runs those manager
QuerySets as real `SUM` SQL without editing `legacy/` or widening
this golden file. The pin's `models.py` stays blocked on Django
1.7-era APIs. That scaffold is not this oracle and is not paper S1.

The golden file still holds 27 traces. Case count alone is not
discrimination. The golden `claim` field remains the replay-only
sentence stored with those traces. This file is the Stage C claim.

`paper_s1` stays unexecuted. `mutation_score` is not stored.
`known_bad_rejected=5` is a probe count, not a kill rate.

Stage D uses this same yardstick against produced rewrite
candidates (`check-stage-d.py`). A candidate accept or reject is
not paper S1 and not a mutation score.

S1 is not a paper execution until the paper says so.
