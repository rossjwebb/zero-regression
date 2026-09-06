# Replication programme

This file maps the public-replication steps to the pull requests that hold the work. Those eight pull requests are merged. It does not run any of those steps.

**None of S1–S3 is a paper execution until the paper says so.** A merge is not a paper result.

Ross: merges happened. The paper stays on the `master` post-approval chain `8ecb0421` / `26075fb8`.

## Map

| Step | What it is | Merged PR |
|---|---|---|
| S1 | Freeze django-accounting, import-only stub, golden replay oracle. Part B: Cursor, Claude Code, and Gemini executed against the 27-trace replay-only oracle (not a score; Codex omitted) is in `subjects/django-accounting/evidence/`. | [PR #1](https://github.com/rossjwebb/zero-regression/pull/1) |
| Path-scrub | Replace leaked machine-local paths so CONFIG hashes change. | [PR #2](https://github.com/rossjwebb/zero-regression/pull/2) — merged. The paper and this repository use the hashes now on `master`. |
| CI + April 91.0 | Pull-request checks, plus a marker that the April 2026 figure of 91.0 is superseded. | [PR #3](https://github.com/rossjwebb/zero-regression/pull/3) |
| S2 | Defects4J Commons-CSV under PIT. | [PR #4](https://github.com/rossjwebb/zero-regression/pull/4) (pin and fail-closed runner); [PR #7](https://github.com/rossjwebb/zero-regression/pull/7) (CI). No mutation score is stored. Pin/runner posture (not a score) is in `subjects/commons-csv/evidence/`. |
| S3 | CardDemo COBOL. | [PR #5](https://github.com/rossjwebb/zero-regression/pull/5) (pin); [PR #6](https://github.com/rossjwebb/zero-regression/pull/6) (GnuCOBOL compile). Compile succeeded. That is not a POSTTRAN job. Pin/compile-runner posture (not a score) is in `subjects/carddemo/evidence/`. |

## Current merged truth

**S1.** The stub is import-only. The golden file holds 27 replay traces. A match is a replay of those traces, not a proof of accounting correctness. Stage C adds a discrimination gate (`subjects/django-accounting/check-discrimination.py`): the good pin still prints the 27-trace replay-only OK line; known-bad probes must fail with a named case mismatch; a golden-echo stub is rejected by golden-independent invariants. `known_bad_rejected=3` is a probe count, not a kill rate. Stage D is a rewrite attempt against that Stage C yardstick (`subjects/django-accounting/evidence/stage-d/`, `check-stage-d.py`): Cursor produced real candidate modules and the gate recorded honest accept/reject; Claude Code and Gemini remain `awaiting-external-run`. A yardstick accept is not generator success. This is still not paper S1. `subjects/django-accounting/evidence/` records Part B as the Stage B historical thin-oracle reading: Cursor, Claude Code, and Gemini executed (`status=executed`, `generators_run=true`, oracle stdout the replay-only OK line, 27 matches / 0 mismatches, `produced=false`). Codex is omitted on purpose. `mutation_score=not-stored`. Domain correctness is out of scope. That three-arm comparison remains a Stage B thin-oracle reading — not “four clean generators” and not success theatre. Stage C posture is `subjects/django-accounting/evidence/discrimination/`. It is not paper S1.

**CI.** When `subjects/django-accounting/oracle.py` is present, the check requires this stdout line and nothing else:

```
ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only
```

If the oracle is missing, the step skips. A skip is not a pass. The old `cases=19` line fails.

**S2.** PIT runs on hash-checked Temurin 11.0.32.1. Subject classfiles are major 52 (`javac --release 8`). Mutators are the named DEFAULTS group. The runner is fail-closed. No mutation score is stored. `subjects/commons-csv/evidence/` records pin identities, the `check-pins.py` gate, and the fail-closed runner claim. That pack is scaffolding+runner-only. It is not paper S2.

**S3.** GnuCOBOL 3.1.2 is hash-checked. Compile of the pinned POSTTRAN program succeeded. The runner then exits 2. `posttran_job=not-run`. A `cobc` failure (`S3 COBC FAIL`, job fails) is split from compile-OK plus harness exit 2 (`S3 HARNESS EXIT 2`, `posttran_job=not-run`, not a GnuCOBOL error). Compile is not a POSTTRAN job. `subjects/carddemo/evidence/` records pin identities, the `check-pins.py` gate, and the fail-closed compile-runner claim (`S3 COMPILE OK` + exit 2 vs `S3 COBC FAIL`). That pack is scaffolding+compile-runner-only. It is not paper S3.

**Dedicated workflows.** `s1-django-accounting-oracle.yml` always runs; requires `cases=27 replay-only`; skip not allowed. The same workflow has a `discrimination` job that runs `check-discrimination.py` (good pin passes; known-bad must fail) and a `stage_d` job that runs `check-stage-d.py`. `s1-django-accounting-stage-d.yml` always runs the same Stage D gate plus its honesty tests; skip not allowed. `s1-django-accounting-part-b.yml` always runs; still requires that same oracle stdout, then `check-part-b.py` and the Part B honesty tests; skip not allowed. `s3-carddemo-compile.yml` always runs; `S3 COMPILE OK` + exit 2 + `posttran_job=not-run`; skip not allowed. Still not paper S1/S3.

## What this file is not

It does not change the mutation harness. It does not rewrite the fixture hashes on `master`. It does not invent a mutation score. It does not rewrite the paper.

`SUBJECTS.md` lists candidate Python subjects. Those candidates are not S1–S3.
