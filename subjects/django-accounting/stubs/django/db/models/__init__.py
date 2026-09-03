# SPDX-License-Identifier: Apache-2.0
"""Import shims for Django 1.7-era ``django.db.models``.

These classes let the 2 December 2017 pin import on Python 3.12.3.
They do not execute Django ORM or SQL. ``QuerySet.filter`` is a no-op.
``aggregate``, ``dued``, and the turnover/debt helpers are absent on
purpose: those are ORM/SQL entry points from the pin's managers, not
behaviour this stub may invent.
"""
from __future__ import annotations

from typing import Any, Iterable


class Field:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs
        self.max_length = kwargs.get("max_length")
        self.default = kwargs.get("default")
        self.null = kwargs.get("null", False)
        self.blank = kwargs.get("blank", False)
        self.attname = kwargs.get("name")


class CharField(Field):
    pass


class TextField(Field):
    pass


class IntegerField(Field):
    pass


class PositiveIntegerField(Field):
    pass


class BooleanField(Field):
    pass


class EmailField(Field):
    pass


class DateField(Field):
    pass


class DecimalField(Field):
    pass


class ForeignKey(Field):
    pass


class ManyToManyField(Field):
    pass


class Sum:
    """Marker imported by the pin's managers. No SQL is issued."""

    def __init__(self, field: str) -> None:
        self.field = field


class QuerySet:
    def __init__(self, items: Iterable[Any] | None = None) -> None:
        self._items = list(items or [])

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def all(self) -> "QuerySet":
        return QuerySet(self._items)

    def first(self) -> Any:
        return self._items[0] if self._items else None

    def distinct(self) -> "QuerySet":
        return QuerySet(self._items)

    def prefetch_related(self, *args: Any, **kwargs: Any) -> "QuerySet":
        return self

    def select_related(self, *args: Any, **kwargs: Any) -> "QuerySet":
        return self

    def filter(self, **kwargs: Any) -> "QuerySet":
        # Django ORM/SQL is not executed. The pin's ProfitsLossCalculator
        # re-checks payment dates in Python after this call.
        return QuerySet(self._items)

    @classmethod
    def as_manager(cls) -> "Manager":
        return Manager(queryset_class=cls)


class RelatedManager:
    def __init__(self, items: Iterable[Any] | None = None) -> None:
        self._items = list(items or [])

    def add(self, *items: Any) -> None:
        self._items.extend(items)

    def all(self) -> QuerySet:
        return QuerySet(self._items)


class Manager:
    def __init__(self, queryset_class: type[QuerySet] = QuerySet) -> None:
        self.queryset_class = queryset_class
        self._items: list[Any] = []

    def all(self) -> QuerySet:
        return self.queryset_class(self._items)

    def add(self, *items: Any) -> None:
        self._items.extend(items)


class _Meta:
    def __init__(self, model: type) -> None:
        self.model = model
        self.verbose_name = model.__name__.lower()
        self.fields: list[Field] = []

    def get_all_related_objects(self) -> list[Any]:
        return []

    def get_field_by_name(self, name: str) -> tuple[Any, Any, bool, bool]:
        return (Field(name=name), self.model, True, False)


class Model:
    objects = Manager()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.pk = kwargs.pop("pk", kwargs.get("id", id(self)))
        self.id = kwargs.get("id", self.pk)
        for key, value in kwargs.items():
            setattr(self, key, value)
        self._meta = _Meta(self.__class__)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Model):
            return NotImplemented
        return self is other or (type(self) is type(other) and self.pk == other.pk)
