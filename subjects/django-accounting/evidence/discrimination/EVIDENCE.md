# S1 Stage C discrimination posture

This pack records the Stage C discrimination gate. It is not a paper execution of S1. It stores no mutation score.

Machine-readable copy: [`posture.json`](posture.json).

The Stage B three-arm thin-oracle record stays in the parent
`evidence/` folder. That pack is historical. This pack does not
rewrite arm receipts and does not claim that generators rewrote code.

## Claims

- `paper_s1=unexecuted`
- `mutation_score=not-stored`
- `oracle=replay + rejects known-bad probes`
- `cases=27`
- `pin=2e61776a653e719a4c15578ab385603a6066c2b6`
- `import_only_stub=true`
- `domain_correctness=out_of_scope`
- `known_bad_rejected=5` (probe count, not a kill rate)
- `invariants=3`
- `golden_echo_rejected=true`
- `clamp_to_zero_rejected=1` (live fixture / yardstick-local
  check count, not a kill rate; known-bad stays 5)
- `golden_widened=false`

## Discrimination proof

Good pin:

```
ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only
```

Known-bad probes (`subjects/django-accounting/discrimination/probes/`)
patch pin callables through an import hook. They do not edit
`legacy/`. Each probe must exit non-zero and name a case the 27-trace
runner already executes:

- `bad_price_tax_zero` → `price_from_tax`
- `bad_fully_paid` → `invoice_fully_paid`
- `bad_profits` → `profits_period_2024_jan_feb`
- `bad_mixed_rate_silent` → `payment_allocation_mixed_rate`
- `bad_unknown_tax_silent` → `price_unknown_tax_access`

Golden-independent invariants (live pin objects, not the golden file):

- excl + tax == incl when tax is known
- total_due_incl == incl − paid
- profits == collected − expenses, including a live org where
  expenses > collected (the 27-trace golden has no negative-profit
  case; clamp-to-zero is rejected here without widening the golden)

Those are arithmetic checks on the pin APIs. They are not accounting
law. The gate also installs a yardstick-local clamp-to-zero
`profits()` and requires that live identity to fail. That is not a
known-bad probe and not a kill rate.

Meta-check: `golden_echo` returns `golden/expected.json` without
calling the pin. Pure replay can print the OK line. The invariant
gate must still reject it (`pin not executed`).

## What is not claimed

- Paper S1 did not run.
- Django ORM and SQL are not executed.
- No mutation score, no kill rate, no percentage.
- The golden file was not widened. Case count alone is not
  discrimination.
- Stage B arm slots are unchanged historical receipts.
