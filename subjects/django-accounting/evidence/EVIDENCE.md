# S1 Part B django-accounting posture evidence

This pack is the **Stage B historical record**. It documents the
three-arm thin-oracle reading on the 27-trace replay. It does not
claim Stage C discrimination.

Stage C (known-bad must fail; golden-independent invariants) is
recorded in [`discrimination/`](discrimination/).

Stage D (rewrite generators versus that Stage C yardstick) is
recorded in [`stage-d/`](stage-d/). Stage D is not paper S1. This
Stage B pack stays historical and is not rewritten as a Stage D
result.

This pack records S1 Part B after all three arms executed against
the existing 27-trace replay-only oracle. Cursor was already on
master. Claude Code and Gemini are recorded on this combined fill.
It is not a paper execution of S1.

Machine-readable copy: [`s1-part-b-posture.json`](s1-part-b-posture.json).

## Claims

- `paper_s1=unexecuted`
- `oracle=replay-only`
- `cases=27`
- `pin=2e61776a653e719a4c15578ab385603a6066c2b6`
- `import_only_stub=true`
- `mutation_score=not-stored`
- `domain_correctness=out_of_scope`
- `status=three-arms-executed`
- `codex_arm=omitted`

No mutation score is stored. The paper has not executed S1. The
three-arm comparison is available as a thin-oracle reading only.

## What Part B is

Part B is the three-arm replication against the already-frozen
django-accounting subject. The arms are Cursor, Claude Code, and
Gemini. Each arm has an output slot under `arms/`.

Codex is not an arm. `codex_arm=omitted` because the lock is three
arms only. That omission is deliberate. It is not an exemption for a
fourth run.

## Arm results

**Cursor (executed).** This Cursor Cloud Agent is the Cursor arm. It
ran the Stage A replication step: the shared probe
`evidence/arms/run-arm-oracle.py` invoked
`python3.12 subjects/django-accounting/oracle.py` on Python 3.12.3.
No new candidate implementation was produced. The golden file was
not widened. Observed oracle stdout was exactly:

```
ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only
```

Match count 27. Mismatch count 0. Exit 0. Receipt:
`arms/cursor/oracle-receipt.json`. `generators_run.cursor=true`.

That 27/0 result is a replay of the recorded traces. It is not a
proof of accounting correctness. It is not clean-generator success.
The honest reading of a zero-mismatch replay is that the oracle is
too thin to discriminate.

**Claude Code (executed).** Zero Regression packaged the Claude Code
slot from a live `run-arm-oracle.py` receipt on Python 3.12.3 under
the Ross/CoS GO. This Cursor cloud agent is the git vehicle /
packager only. It is not a second Cursor arm and not a Claude · Max
chat run (browser paste timed out; no Claude · Max session is
claimed). The work order is `arms/claude-code/PROMPT.md` (also
stored on `arm.json` as `prompt`). Numbers were copied from the
live receipt only. No new candidate implementation was produced
(`produced=false`). The golden file was not widened. Observed
oracle stdout was exactly:

```
ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only
```

Match count 27. Mismatch count 0. Exit 0. Receipt:
`arms/claude-code/oracle-receipt.json`. `generators_run.claude_code=true`.

**Gemini (executed).** CoS ran the shared probe on Mac Python 3.12.3
and Gemini attested the live receipt. Gemini web could not run a
local shell. No new candidate implementation was produced
(`produced=false`). The golden file was not widened. Observed
oracle stdout was exactly:

```
ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only
```

Match count 27. Mismatch count 0. Exit 0. Receipt:
`arms/gemini/oracle-receipt.json`. `generators_run.gemini=true`.
The historical work order remains `arms/gemini/PROMPT.md`.

No arm remains `awaiting-external-run`. `claims.generators_run` is
true because the three-arm set has now run. The comparison is
available only as the same thin-oracle reading on every arm. That
is not paper S1 and not clean-generator success.

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

All three arms reported zero mismatches. The honest reading is that
the oracle is too thin to discriminate. That result is not “four
clean generators”. It is not success theatre. It is not paper S1.

## What is recorded

- Pin `2e61776a653e719a4c15578ab385603a6066c2b6`, 27 replay-only
  cases, import-only stub.
- `oracle.py` is the existing gate. On this tree it was run with
  Python 3.12.3 and exited 0 with the replay-only OK line. That exit
  is a replay of recorded traces, not domain correctness and not
  paper S1.
- `check-part-b.py` is the Part B honesty gate. It still requires
  that same oracle stdout line. It does not store a mutation score.
- Cursor, Claude Code, and Gemini arm output (`status=executed`,
  `generators_run=true`) each with a 27/0 receipt and
  `candidate_artefacts.produced=false`.

## What is not recorded

- No mutation score, no kill rate, no percentage, no CERTIFICATE
  record in the harness log.
- No invented oracle numbers. Gemini numbers were copied from the
  CoS-run receipt.
- No Codex arm and no Codex exemption.
- No claim that paper S1 ran.
- No widening of the 27-trace golden file.
- No claim that four clean generators produced a paper result.
