# S1 ORM path — org aggregates scaffold

This pack records a live Django ORM/SQL path for organisation-level
aggregates. It is not paper S1. It stores no mutation score.

Machine-readable copy: [`posture.json`](posture.json).

## Claims

- `paper_s1=unexecuted`
- `mutation_score=not-stored`
- `path=pin-managers-queryset-aggregate`
- `orm_sql_executed=true` (this scaffold only; the 27-trace oracle still does not run ORM)
- `django=5.2.17` on Python 3.12.3
- `pin=2e61776a653e719a4c15578ab385603a6066c2b6`
- `pin_models_imported=false`
- `blocked=pin-models-django-1.7-apis`
- `domain_correctness=out_of_scope`

No mutation score is stored. No kill rate is stored. The paper has
not executed S1.

## What runs

`subjects/django-accounting/orm/run-org-aggregates.py` installs no
stub. It boots pinned Django 5.2.17 against SQLite `:memory:` and
imports the pin's `InvoiceQuerySet` / `BillQuerySet` from
`legacy/accounting/apps/books/managers.py`. Those classes call
`QuerySet.aggregate(Sum(...))`. The captured SQL contains `SUM(`
and the overdue path filters `date_dued` in SQL.

Organisation properties on the scaffold (`turnover_*`, `debts_*`,
`overdue_total`) are the same formulas as the pin's `Organization`.
The 27-trace golden file is not widened. `organization_derived` and
`overdue_total` remain absent from `golden/expected.json`.

## What is still blocked

The pin's `legacy/accounting/apps/books/models.py` does not import
on Django 5.2 + Python 3.12.3. First failure:
`django.core.urlresolvers` (removed in Django 2.0). After a shim,
`SortedDict` is gone. The frozen slice also lacks `people.Client` /
`people.Employee`, and every `ForeignKey` omits `on_delete`.

Django 1.7 (the pin era) does not run on Python 3.12.3. This
scaffold does not claim a Django 1.7 execution.

`Payment` on the scaffold is a plain FK with `related_name="payments"`,
not the pin's `GenericRelation`. The lookup `payments__amount` is the
same name the pin's `total_paid` helper uses.

`legacy/` is not edited. The import-only stub is unchanged:
`QuerySet.filter` is still a no-op and there is still no
`aggregate` on the stub.

## What this is not

- Not paper S1.
- Not a mutation score.
- Not a widening of the 27-trace golden file.
- Not a claim that the pin's `models.py` loaded.
- Not Stage C/D weakening. Those gates must stay green.
