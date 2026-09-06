# S1 ORM / SQL path (org aggregates)

Separate Django 5.2.17 pin plus a scaffold app. `legacy/` is not
edited. The import-only stub is not this path.

```bash
python3.12 -m pip install --require-hashes -r subjects/django-accounting/orm/requirements.lock
python3.12 subjects/django-accounting/orm/write-lock.py --check
python3.12 subjects/django-accounting/orm/run-org-aggregates.py
python3.12 subjects/django-accounting/check-orm.py
```

A missing Django install is `blocked=django-not-installed`, not a
pass. Pin `models.py` remains `blocked=pin-models-django-1.7-apis`.
This is not paper S1. `mutation_score` is not stored.
