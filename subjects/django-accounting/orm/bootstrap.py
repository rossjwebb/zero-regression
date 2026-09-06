# SPDX-License-Identifier: Apache-2.0
"""Boot the scaffold app under real Django. Never put stubs on sys.path."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ORM = Path(__file__).resolve().parent
SUBJECT = ORM.parent
LEGACY = SUBJECT / "legacy"
STUBS = SUBJECT / "stubs"
PIN = "2e61776a653e719a4c15578ab385603a6066c2b6"
DJANGO_VERSION = "5.2.17"


def refuse_stubs() -> None:
    stub = str(STUBS)
    if stub in sys.path:
        sys.path.remove(stub)
    django_file = sys.modules.get("django")
    if django_file is not None:
        path = getattr(django_file, "__file__", "") or ""
        if "subjects/django-accounting/stubs" in path.replace("\\", "/"):
            raise RuntimeError("S1 ORM FAIL-CLOSED: stub django leaked onto sys.modules")


def ensure_paths() -> None:
    refuse_stubs()
    for path in (str(ORM), str(LEGACY)):
        if path not in sys.path:
            sys.path.insert(0, path)


def require_real_django():
    try:
        import django
        from django.db.models import QuerySet, Sum
    except ImportError as exc:
        raise RuntimeError(
            "S1 ORM FAIL-CLOSED: blocked=django-not-installed "
            f"(need Django {DJANGO_VERSION} on Python 3.12.3)"
        ) from exc
    refuse_stubs()
    if django.get_version() != DJANGO_VERSION:
        raise RuntimeError(
            f"S1 ORM FAIL-CLOSED: blocked=django-version-mismatch "
            f"need {DJANGO_VERSION} got {django.get_version()}"
        )
    if not hasattr(QuerySet, "aggregate"):
        raise RuntimeError("S1 ORM FAIL-CLOSED: QuerySet.aggregate missing; stub leaked")
    if not QuerySet.__module__.startswith("django.db"):
        raise RuntimeError(
            f"S1 ORM FAIL-CLOSED: QuerySet is not Django ORM ({QuerySet.__module__})"
        )
    if Sum.__module__ != "django.db.models.aggregates":
        raise RuntimeError(f"S1 ORM FAIL-CLOSED: Sum is not Django ORM ({Sum.__module__})")
    return django


def setup():
    ensure_paths()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "s1_org_aggregates.settings")
    django = require_real_django()
    django.setup()
    from django.db import connection

    from s1_org_aggregates.models import Bill, Invoice, Organization, Payment

    with connection.schema_editor() as editor:
        editor.create_model(Organization)
        editor.create_model(Invoice)
        editor.create_model(Bill)
        editor.create_model(Payment)
    return {
        "django": django,
        "Organization": Organization,
        "Invoice": Invoice,
        "Bill": Bill,
        "Payment": Payment,
        "connection": connection,
    }


def probe_pin_models() -> dict[str, str]:
    """Record why the pin's models.py cannot load. Do not invent a success."""
    ensure_paths()
    require_real_django()
    try:
        import accounting.apps.books.models  # noqa: F401
    except Exception as exc:
        return {
            "imported": "false",
            "blocked": f"{type(exc).__name__}: {exc}",
        }
    return {"imported": "true", "blocked": ""}
