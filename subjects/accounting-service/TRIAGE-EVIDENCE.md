# TRIAGE-EVIDENCE

## update__mutmut_12 (`newBalance = Decimal("0.00")` → `None`)

Initializer is overwritten on both operator arms before the first read; `_getOperatorBySymbolAndSide` returns only PLUS or MINUS.

```
 94     def _getOperatorBySymbolAndSide(self, symbol: TransactionSymbolEnum, side: AccountsSideEnum) -> OperatorEnum:
 97                 return OperatorEnum.PLUS
 99                 return OperatorEnum.MINUS
102                 return OperatorEnum.PLUS
104                 return OperatorEnum.MINUS
106             return OperatorEnum.PLUS
108             return OperatorEnum.MINUS
124         newBalance = Decimal("0.00")
139         if operator == OperatorEnum.PLUS:
143             newBalance = balance + txnAmt
144         elif operator == OperatorEnum.MINUS:
147             newBalance = balance - txnAmt
149         entry.balance = newBalance
```

## update__mutmut_142 (`newLastBal = Decimal("0.00")` → `None`)

Initializer is overwritten on the PLUS arm and the else (MINUS) arm before the first read.

```
193                 newLastBal = Decimal("0.00")
195                 if operator == OperatorEnum.PLUS:
199                     newLastBal = lastBal + txnAmt
200                 else:
203                     newLastBal = lastBal - txnAmt
205                 account.lastBalance = newLastBal
```

## update__mutmut_105 (`elif day_gap > 1` → `>= 1`)

The `== 1` arm is consumed by the preceding `if`, so the `elif` never sees `day_gap == 1`.

```
154             day_gap = (txnDate - latestTxnDate).days
155             if day_gap == 1:
156                 account.lastBalance = balance
169                     account.crTransactionAmt = txnAmt
170             elif day_gap > 1:
```

## update__mutmut_31 (`frozenAmt <` → `<=`)

A zero value is already zero; the inclusive bound normalises zero to zero.

```
136         if frozenAmt < Decimal("0.00"):
137             frozenAmt = Decimal("0.00")
```
