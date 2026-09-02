# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from datetime import date
from decimal import Decimal
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

    def distinct(self) -> "QuerySet":
        return QuerySet(self._items)

    def prefetch_related(self, *args: Any) -> "QuerySet":
        return self

    def select_related(self, *args: Any) -> "QuerySet":
        return self

    def filter(self, **kwargs: Any) -> "QuerySet":
        items = self._items
        for key, expected in kwargs.items():
            parts = key.split("__")
            if len(parts) > 2:
                # Related-field lookups are re-applied in the calculator's payment loop.
                continue
            if len(parts) == 2 and parts[1] == "lte":
                items = [item for item in items if _lookup(item, parts[0]) is not None and _lookup(item, parts[0]) <= expected]
            elif len(parts) == 2 and parts[1] == "gte":
                items = [item for item in items if _lookup(item, parts[0]) is not None and _lookup(item, parts[0]) >= expected]
            elif "__" in key:
                continue
            else:
                items = [item for item in items if _matches(item, key, expected)]
        return QuerySet(items)

    def first(self) -> Any:
        return self._items[0] if self._items else None

    def aggregate(self, **kwargs: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, expr in kwargs.items():
            field = getattr(expr, "field", None)
            total = None
            for item in self._items:
                value = _lookup(item, field) if field else None
                if value is None:
                    continue
                total = value if total is None else total + value
            result[key] = total
        return result

    def dued(self) -> "QuerySet":
        return self.filter(date_dued__lte=date.today())

    def turnover_excl_tax(self) -> Any:
        return self.aggregate(sum=Sum("total_excl_tax"))["sum"]

    def turnover_incl_tax(self) -> Any:
        return self.aggregate(sum=Sum("total_incl_tax"))["sum"]

    def debts_excl_tax(self) -> Any:
        return self.turnover_excl_tax()

    def debts_incl_tax(self) -> Any:
        return self.turnover_incl_tax()

    def total_paid(self) -> Any:
        return self.aggregate(sum=Sum("payments__amount"))["sum"] or Decimal("0")

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

    def filter(self, **kwargs: Any) -> QuerySet:
        return self.all().filter(**kwargs)

    def dued(self) -> QuerySet:
        return self.all().dued()

    def turnover_excl_tax(self) -> Any:
        return self.all().turnover_excl_tax()

    def turnover_incl_tax(self) -> Any:
        return self.all().turnover_incl_tax()

    def debts_excl_tax(self) -> Any:
        return self.all().debts_excl_tax()

    def debts_incl_tax(self) -> Any:
        return self.all().debts_incl_tax()

    def total_paid(self) -> Any:
        return self.all().total_paid() or Decimal("0")


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


def _lookup(item: Any, field: str) -> Any:
    current = item
    for part in field.split("__"):
        if current is None:
            return None
        if part == "amount" and hasattr(current, "all"):
            values = [getattr(pay, "amount", None) for pay in current.all()]
            values = [value for value in values if value is not None]
            if not values:
                return None
            total = values[0]
            for value in values[1:]:
                total += value
            return total
        current = getattr(current, part, None)
    return current


def _matches(item: Any, key: str, expected: Any) -> bool:
    value = getattr(item, key, None)
    if value is expected:
        return True
    if isinstance(value, Decimal) or isinstance(expected, Decimal):
        return value == expected
    return value == expected
