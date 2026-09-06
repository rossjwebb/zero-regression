# S1 Stage D — Claude Code arm (paste this whole block)

You are the Claude Code generator arm for S1 Stage D on
https://github.com/rossjwebb/zero-regression

Base: current `master` tip that includes Stage C discrimination
(`6ab6d0a`). Do not invent results. Do not merge. Do not fake a run.

Stage B was a thin-oracle probe (`produced=false`). Stage C made the
yardstick discriminate. Stage D must *produce* candidate rewrites and
run them against that yardstick. This is not paper S1.

## Locks (binding)

1. KEEP 27 traces / pin `2e61776a653e719a4c15578ab385603a6066c2b6`. DO NOT widen `subjects/django-accounting/golden/expected.json`.
2. Never edit `subjects/*/legacy/` or `subjects/*/golden/`.
3. Arms: Cursor, Claude Code, Gemini only. NO Codex.
4. `paper_s1=unexecuted`. `mutation_score=not-stored` (string, never a number). No kill-rate %.
5. Do not weaken Stage C. Good pin must still print the replay-only OK line. `check-discrimination.py` must still reject the three known-bad probes and the golden echo.
6. Leave Stage B `evidence/arms/*/arm.json` historical. Write Stage D output under `evidence/stage-d/`.
7. No FinTx/CONFIG hash rewrites. No paper edits. No force-push.

## Yardstick (must stay green on the good pin)

```bash
python3.12 subjects/django-accounting/oracle.py
# exact: ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only

python3.12 subjects/django-accounting/check-discrimination.py
# DISCRIMINATION OK (known-bad×3 reject + golden-echo reject + invariants×3)
```

## What to do

Produce 2–3 small competing rewrites of a narrow slice the oracle
already exercises (`Price`, sale totals, or `ProfitsLossCalculator`).
Store them under:

`subjects/django-accounting/evidence/stage-d/arms/claude-code/candidates/`

Apply them with the existing import-hook harness. Do not edit `legacy/`.

```bash
python3.12 subjects/django-accounting/evidence/stage-d/evaluate-candidate.py --candidate <name>
```

Copy the printed JSON receipt. Do not type numbers from memory.

Fill `subjects/django-accounting/evidence/stage-d/arms/claude-code/arm.json`:

- `status=executed` and `generators_run=true` only if you actually ran
- `candidate_artefacts.produced=true` with real paths, or `produced=false` with a reason
- each candidate's oracle exit, named mismatched cases, invariant failures
- `paper_s1=unexecuted`
- `mutation_score=not-stored`
- `discrimination_gate=required`

If you did not run, leave `status=awaiting-external-run` and
`generators_run=false`. Do not invent stdout.

A yardstick accept is not generator success and not paper S1.
A yardstick reject is the expected reading for an intentional weak rewrite.

## Must not

- Invent Claude Code run results
- Claim Cursor's receipts as yours
- Store a numeric mutation score or kill rate
- Claim paper S1 executed
- Add a Codex arm
- Rewrite Stage B receipts to look like Stage D
