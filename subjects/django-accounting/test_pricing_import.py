# SPDX-License-Identifier: Apache-2.0
from decimal import Decimal

from accounting.libs.prices import Price


def test_pinned_price_object_imports_under_the_django_stub() -> None:
    price = Price("EUR", Decimal("10.00"), tax=Decimal("2.00"))
    assert price.is_tax_known
    assert price.incl_tax == Decimal("12.00")
