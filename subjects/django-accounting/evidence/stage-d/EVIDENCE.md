# S1 Stage D rewrite-generator posture

Stage D is a rewrite attempt against the Stage C discriminating
yardstick. It is not paper S1.

Machine-readable copy: [`posture.json`](posture.json).

Stage B remains the historical thin-oracle record in the parent
`evidence/` folder (`produced=false` on every arm). This pack does
not rewrite those receipts. Stage C remains `evidence/discrimination/`.

## Claims

- `stage=D`
- `paper_s1=unexecuted`
- `mutation_score=not-stored`
- `discrimination_gate=required`
- `produced=true` (Cursor arm only)
- `domain_correctness=out_of_scope`
- `codex_arm=omitted`

No mutation score is stored. No kill rate is stored. The paper has
not executed S1.

## What Stage D is

Cursor produced three competing rewrites of a narrow slice the
oracle already exercises (`Price` / collected profits). Each rewrite
lives under `arms/cursor/candidates/` and is applied through
`apply.py` (import hook). `legacy/` is not edited.

Each candidate was evaluated with `evaluate-candidate.py` against
the Stage C gate: 27-trace replay plus the three golden-independent
invariants. Receipts are under `arms/cursor/receipts/`.

## Cursor outcomes (live, Python 3.12.3)

**price-faithful** — accepted. Replay printed

```
ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only
```

Match count 27. Mismatch count 0. Exit 0. Invariants held. That
accept means this rewrite still matched the recorded traces and the
arithmetic checks. It is not generator success and not paper S1.

**price-tax-ignored** — rejected. Intentional weak Price that drops
tax. Oracle exit 1. Thirteen named mismatches including
`price_from_tax`. Invariant failure: `excl+tax != incl`.

**profits-no-window** — rejected. Intentional weak
`ProfitsLossCalculator` that drops the in-process payment date
window. Oracle exit 1. Named mismatches:
`profits_period_2024_jan_feb`, `profits_dated_invoice_only`.
Invariants still held (`profits == collected - expenses`).

The yardstick rejected at least one produced candidate. The good
pin, unpatched, still prints the replay-only OK line.
`check-discrimination.py` still reports DISCRIMINATION OK.

## External arms

**Claude Code** — `awaiting-external-run`. Paste-ready work order:
[`arms/claude-code/PROMPT.md`](arms/claude-code/PROMPT.md). No
Claude run is claimed.

**Gemini** — `executed` (2026-09-06). Mindway Gemini designed three
candidates against a made-up Price API; raw designs sit under
`arms/gemini/design/`. CoS adapted intents to the pin API, evaluated on
Mac Python 3.12 with `evaluate-candidate.py --arm gemini`, and filed live
receipts. `faithful-price-round` accepted; `weak-tax-truncation` rejected.
PR #23 recorded `weak-profits-zero-override` as accepted because the
27-trace golden has no negative-profit case — that receipt was an
honest reading of the then-yardstick, not a generator success. The
yardstick now includes a golden-independent expenses>collected live
org, so the same clamp-to-zero rewrite is rejected by live
invariants going forward (replay still matches 27/0). Not paper S1.
Work order: [`arms/gemini/PROMPT.md`](arms/gemini/PROMPT.md).

Codex is omitted on purpose.

## What is not claimed

- Paper S1 did not run.
- Generators did not “succeed”.
- Django ORM and SQL are not executed.
- No mutation score, no kill rate, no percentage.
- The golden file was not widened.
- Stage B thin-oracle 27/0 receipts are not a Stage D result.
