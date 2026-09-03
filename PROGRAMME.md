# Replication programme

This file maps the unexecuted public-replication steps to the draft pull requests that already hold the work. It does not run any of those steps.

**None of S1–S3 is a paper execution until the matching pull request is merged and the paper says so.** A draft is not a result.

Ross: no merges. The paper stays on the `master` post-approval chain `60df647f` / `fe677dfc`.

## Map

| Step | What it is | Draft PR |
|---|---|---|
| S1 | Freeze django-accounting, import-only stub, golden replay oracle. | [PR #1](https://github.com/rossjwebb/zero-regression/pull/1) |
| Path-scrub | Replace leaked machine-local paths so CONFIG hashes change. | [PR #2](https://github.com/rossjwebb/zero-regression/pull/2) — parked. The paper and this repository still use the hashes on `master`. |
| CI + April 91.0 | Pull-request checks, plus a marker that the April 2026 figure of 91.0 is superseded. | [PR #3](https://github.com/rossjwebb/zero-regression/pull/3) |
| S2 | Defects4J Commons-CSV under PIT. | [PR #4](https://github.com/rossjwebb/zero-regression/pull/4) (pin and fail-closed runner); [PR #7](https://github.com/rossjwebb/zero-regression/pull/7) (CI). No mutation score is stored. |
| S3 | CardDemo COBOL. | [PR #5](https://github.com/rossjwebb/zero-regression/pull/5) (pin); [PR #6](https://github.com/rossjwebb/zero-regression/pull/6) (GnuCOBOL compile). Compile succeeded. That is not a green test job. |

## Current unmerged truth

**PR #1 follow-up.** The stub is import-only. The golden file holds 27 replay traces. A match is a replay of those traces, not a proof of accounting correctness. This is still not paper S1.

**PR #3 CI.** When `subjects/django-accounting/oracle.py` is present, the check requires this stdout line and nothing else:

```
ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only
```

If the oracle is missing, the step skips. A skip is not a pass. The old `cases=19` line fails.

**PR #4 / PR #7.** PIT runs on hash-checked Temurin 11.0.32.1. Subject classfiles are major 52 (`javac --release 8`). Mutators are the named DEFAULTS group. The runner is fail-closed. No mutation score is stored.

**PR #6.** GnuCOBOL 3.1.2 is hash-checked. Compile of the pinned POSTTRAN program succeeded. The runner then exits 2. `posttran_job=not-run`.

**Dedicated workflows.** PR #1 now has `s1-django-accounting-oracle.yml` (always runs; requires `cases=27 replay-only`; skip not allowed). PR #6 now has `s3-carddemo-compile.yml` (always runs; `S3 COMPILE OK` + exit 2 + `posttran_job=not-run`; skip not allowed). Still not paper S1/S3.

## What this file is not

It does not merge any pull request. It does not change the mutation harness. It does not rewrite the fixture hashes on `master` or the hashes proposed in PR #2. It does not invent a mutation score.

`SUBJECTS.md` lists candidate Python subjects. Those candidates are not S1–S3.
