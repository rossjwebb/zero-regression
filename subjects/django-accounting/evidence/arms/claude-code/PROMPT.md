# S1 Part B — Claude Code arm (paste this whole block)

You are the Claude Code generator arm for S1 Part B on
https://github.com/rossjwebb/zero-regression

Base the work on current `master` after PR #14 (Stage A posture).
Do not invent results. Do not merge.

## Locks (binding)

1. KEEP 27 traces / pin `2e61776a653e719a4c15578ab385603a6066c2b6`. DO NOT widen `subjects/django-accounting/golden/expected.json`.
2. Arms: Cursor, Claude Code, Gemini only. NO Codex.
3. Certificate language: replay-only oracle, 27 recorded traces, domain correctness out of scope.
4. If the oracle reports zero mismatches: the honest reading is that the oracle is too thin to discriminate — NOT clean-generator success, NOT “four clean generators”, NOT success theatre, NOT paper S1.
5. `paper_s1=unexecuted` still. `mutation_score=not-stored`. No fake scores. No FinTx/CONFIG hash rewrites. No paper edits. No force-push.
6. Never edit files under `subjects/*/legacy/` or `subjects/*/golden/`.

## What to do

From the repository root, with Python 3.12.3:

```bash
python3.12 subjects/django-accounting/evidence/arms/run-arm-oracle.py
```

That script runs `subjects/django-accounting/oracle.py` and prints a JSON receipt.
It does not write `arm.json` for you.

Then fill `subjects/django-accounting/evidence/arms/claude-code/arm.json` with an honest executed record:

- `status=executed`
- `generators_run=true`
- `method` plus this prompt text
- whether you produced any new candidate artefacts (if you only ran the existing pin, say `produced=false`)
- `oracle.stdout` exactly as printed (copy the receipt; do not type it from memory)
- `match_count` / `mismatch_count` / `exit` from the receipt
- `paper_s1=unexecuted`
- `mutation_score=not-stored` (string, never a number)
- `zero_mismatch_means=oracle too thin to discriminate` if `mismatch_count` is 0

If the oracle did not actually run, leave `status=awaiting-external-run` and `generators_run=false`. Do not invent stdout.

Expected oracle stdout if the pin still matches:

```
ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only
```

That line is a replay of 27 recorded traces. It is not a proof of accounting correctness. Django ORM and SQL are not executed. The stub is import-only.

## Must not

- Invent Claude Code run results without running the oracle
- Widen the golden file
- Store a numeric mutation score or kill rate
- Claim paper S1 executed
- Add a Codex arm
- Treat a 27/0 receipt as generator success
