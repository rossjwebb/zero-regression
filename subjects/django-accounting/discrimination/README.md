# S1 Stage C discrimination

This directory is the discrimination proof for the django-accounting
oracle. It does not rewrite `legacy/`. It does not store a mutation
score.

## What it proves

- The good pin still prints
  `ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only`.
- Three known-bad probes, loaded by an import hook, fail that replay
  for a named already-executed case.
- A golden-echo stub that returns `golden/expected.json` without
  calling the pin can print that same OK line, and is still rejected
  by the invariant gate.

`known_bad_rejected=3` is a probe count. It is not a kill rate.

## Known-bad probes

| Probe | Patched callable | Must mismatch |
|---|---|---|
| `bad_price_tax_zero` | `Price.tax` / wrong `incl_tax` | `price_from_tax` |
| `bad_fully_paid` | `AbstractSale.is_fully_paid` inverted | `invoice_fully_paid` |
| `bad_profits` | `ProfitsLossCalculator.process_generator` drops the payment date window | `profits_period_2024_jan_feb` |

## Invariants (golden-independent)

Checked on live pin objects, not by reading the golden file:

- `excl + tax == incl` when tax is known
- `total_due_incl_tax == total_incl_tax - total_paid`
- `profits() == total_collected() - total_expenses()`

These are arithmetic consistency checks on the pin APIs the oracle
already calls. They are not accounting-law certification.

## How to run

From the repository root, Python 3.12.3:

```bash
python3.12 subjects/django-accounting/oracle.py
python3.12 subjects/django-accounting/check-discrimination.py
```

The second command is fail-closed: a known-bad that exits 0 fails
the gate.
