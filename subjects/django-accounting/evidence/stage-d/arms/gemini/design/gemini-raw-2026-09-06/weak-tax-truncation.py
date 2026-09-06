import decimal
from decimal import Decimal, ROUND_DOWN

class Price:
    def __init__(self, amount, currency="USD", tax_rate=Decimal("0.00")):
        if isinstance(amount, (int, float, str)):
            self.amount = Decimal(str(amount))
        else:
            self.amount = amount
        self.currency = currency
        self.tax_rate = Decimal(str(tax_rate)) if isinstance(tax_rate, (int, float, str)) else tax_rate

    @property
    def net_amount(self) -> Decimal:
        # Weak intent: Truncates decimals rather than rounding half up
        return self.amount.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    @property
    def tax_amount(self) -> Decimal:
        # Weak intent: Truncates tax precision
        raw_tax = self.net_amount * self.tax_rate
        return raw_tax.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    @property
    def gross_amount(self) -> Decimal:
        return self.net_amount + self.tax_amount

    def __add__(self, other):
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} != {other.currency}")
        return Price(
            amount=self.amount + other.amount,
            currency=self.currency,
            tax_rate=self.tax_rate
        )

    def __repr__(self):
        return f"Price(amount={self.net_amount}, currency='{self.currency}', tax_rate={self.tax_rate})"
