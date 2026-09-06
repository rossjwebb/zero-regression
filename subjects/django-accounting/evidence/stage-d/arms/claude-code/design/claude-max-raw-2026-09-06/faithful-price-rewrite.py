"""Price value object for django-accounting.

Arm:    claude-code
Slice:  Price
Pin:    2e61776a653e719a4c15578ab385603a6066c2b6
Intent: faithful-rewrite (behaviour-preserving)
"""


class TaxNotKnown(Exception):
    """
    Raised when a tax-inclusive amount is requested but the applicable tax
    is not (yet) known.

    Defined here for callers; ``Price`` itself does not raise it.
    """


class Price(object):
    """
    A currency code, a tax-exclusive amount, and -- when it is known -- the
    matching tax-inclusive amount.

    ``incl_tax`` is only assigned when the tax is known.  Reading it while
    ``is_tax_known`` is False therefore raises ``AttributeError``; that is
    the pinned behaviour and is preserved deliberately.
    """

    def __init__(self, currency, excl_tax, incl_tax=None, tax=None):
        self.currency = currency
        self.excl_tax = excl_tax
        if incl_tax is not None:
            self.incl_tax = incl_tax
            self.is_tax_known = True
        elif tax is not None:
            self.incl_tax = excl_tax + tax
            self.is_tax_known = True
        else:
            self.is_tax_known = False

    def _get_tax(self):
        return self.incl_tax - self.excl_tax

    def _set_tax(self, value):
        self.incl_tax = self.excl_tax + value
        self.is_tax_known = True

    tax = property(_get_tax, _set_tax)

    def _require_same_currency(self, other):
        if self.currency != other.currency:
            raise ValueError(
                "Cannot combine prices in different currencies "
                "(%s and %s)" % (self.currency, other.currency))

    def __add__(self, other):
        if not isinstance(other, Price):
            return NotImplemented
        self._require_same_currency(other)
        excl_tax = self.excl_tax + other.excl_tax
        if self.is_tax_known and other.is_tax_known:
            return self.__class__(self.currency, excl_tax,
                                  incl_tax=self.incl_tax + other.incl_tax)
        return self.__class__(self.currency, excl_tax)

    def __sub__(self, other):
        if not isinstance(other, Price):
            return NotImplemented
        self._require_same_currency(other)
        excl_tax = self.excl_tax - other.excl_tax
        if self.is_tax_known and other.is_tax_known:
            return self.__class__(self.currency, excl_tax,
                                  incl_tax=self.incl_tax - other.incl_tax)
        return self.__class__(self.currency, excl_tax)

    def __mul__(self, factor):
        if isinstance(factor, Price):
            return NotImplemented
        excl_tax = self.excl_tax * factor
        if self.is_tax_known:
            return self.__class__(self.currency, excl_tax,
                                  incl_tax=self.incl_tax * factor)
        return self.__class__(self.currency, excl_tax)

    __rmul__ = __mul__

    def __neg__(self):
        if self.is_tax_known:
            return self.__class__(self.currency, -self.excl_tax,
                                  incl_tax=-self.incl_tax)
        return self.__class__(self.currency, -self.excl_tax)

    def __eq__(self, other):
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            return False
        if self.excl_tax != other.excl_tax:
            return False
        if self.is_tax_known != other.is_tax_known:
            return False
        if self.is_tax_known and self.incl_tax != other.incl_tax:
            return False
        return True

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other):
        if not isinstance(other, Price):
            return NotImplemented
        self._require_same_currency(other)
        return self.excl_tax < other.excl_tax

    def __le__(self, other):
        if not isinstance(other, Price):
            return NotImplemented
        self._require_same_currency(other)
        return self.excl_tax <= other.excl_tax

    def __gt__(self, other):
        if not isinstance(other, Price):
            return NotImplemented
        self._require_same_currency(other)
        return self.excl_tax > other.excl_tax

    def __ge__(self, other):
        if not isinstance(other, Price):
            return NotImplemented
        self._require_same_currency(other)
        return self.excl_tax >= other.excl_tax

    def __hash__(self):
        incl = self.incl_tax if self.is_tax_known else None
        return hash((self.currency, self.excl_tax, incl))

    def __bool__(self):
        if self.is_tax_known:
            return bool(self.excl_tax) or bool(self.incl_tax)
        return bool(self.excl_tax)

    __nonzero__ = __bool__

    def __repr__(self):
        if self.is_tax_known:
            return ("%s(currency=%r, excl_tax=%r, incl_tax=%r, tax=%r)"
                    % (self.__class__.__name__, self.currency,
                       self.excl_tax, self.incl_tax, self.tax))
        return ("%s(currency=%r, excl_tax=%r)"
                % (self.__class__.__name__, self.currency, self.excl_tax))
