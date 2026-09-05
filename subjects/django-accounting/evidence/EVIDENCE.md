# S1 Part B django-accounting posture evidence

This pack records the honesty posture for S1 Part B: three-arm
replication scaffolding against the existing replay-only oracle. It is
not a paper execution of S1.

Machine-readable copy: [`s1-part-b-posture.json`](s1-part-b-posture.json).

## Claims

- `paper_s1=unexecuted`
- `oracle=replay-only`
- `cases=27`
- `pin=2e61776a653e719a4c15578ab385603a6066c2b6`
- `import_only_stub=true`
- `mutation_score=not-stored`
- `domain_correctness=out_of_scope`
- `status=scaffolding+three-arm-not-run`
- `codex_arm=omitted`

No mutation score is stored. The paper has not executed S1. This pack
is scaffolding only. The three generator arms have not been run.

## What Part B is

Part B is the three-arm replication scaffold for the already-frozen
django-accounting subject. The arms are Cursor, Claude Code, and
Gemini. Each arm has an output slot under `arms/`. Those slots are
empty of results: `status=not-run`, `generators_run=false`.

Codex is not an arm. `codex_arm=omitted` because the lock is three
arms only. That omission is deliberate. It is not an exemption for a
fourth run.

## What the oracle is, and is not

The oracle is a replay of 27 recorded traces against the pin
`2e61776a653e719a4c15578ab385603a6066c2b6`. A match prints:

```
ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only
```

That line means those same calls still produce the same JSON. It is
not a proof of accounting correctness. Domain correctness is out of
scope. The oracle does not certify tax law, double-entry invariants,
or collected-versus-accrual profits. Django ORM and SQL are not
executed. The stub is import-only.

The golden file stays at 27 traces. This pack does not add cases and
does not widen `golden/expected.json`.

## Certificate language

Any certificate or evidence for Part B must say, explicitly:

- the oracle is replay-only
- there are 27 recorded traces
- domain correctness is out of scope

If a later three-arm run reports zero mismatches across arms, the
honest reading is that the oracle is too thin to discriminate. That
result is not “four clean generators”. It is not success theatre. It
is not paper S1.

This pack does not report a three-arm comparison. The arms have not
run. There is no mismatch count to interpret yet. The zero-mismatch
rule is recorded now so a later empty comparison cannot be dressed up
as a clean generator result.

## What is recorded

- Pin `2e61776a653e719a4c15578ab385603a6066c2b6`, 27 replay-only
  cases, import-only stub.
- `oracle.py` is the existing gate. On this tree it was run with
  Python 3.12.3 and exited 0 with the replay-only OK line. That exit
  is a replay of recorded traces, not domain correctness and not
  paper S1.
- `check-part-b.py` is the Part B honesty gate. It still requires
  that same oracle stdout line. It does not run a generator and does
  not store a mutation score.
- Three arm output slots (Cursor, Claude Code, Gemini), each
  `status=not-run` / `generators_run=false`.

## What is not recorded

- No mutation score, no kill rate, no percentage, no CERTIFICATE
  record in the harness log.
- No generator survivors, no invented arm results.
- No Codex arm and no Codex exemption.
- No claim that paper S1 ran.
- No widening of the 27-trace golden file.
