# Import stubs (not Django)

These modules exist so the 2 December 2017 MIT pin
`dulacp/django-accounting` `2e61776a653e719a4c15578ab385603a6066c2b6`
can be imported on the pinned interpreter (Python 3.12.3).

They are not Django. They do not open a database. They do not compile
or run SQL. `QuerySet.filter` is a no-op. There is no `aggregate`.
Org-level aggregates use the separate Django 5.2.17 pin under `../orm/`.

The subject remains the frozen files under `../legacy/`. Do not edit
those files. The upstream MIT licence is `../legacy/LICENSE`.
