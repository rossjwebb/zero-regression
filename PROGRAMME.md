# Replication programme

This file maps the unexecuted public-replication steps to the draft pull requests that already hold the work. It does not run any of those steps.

**None of S1–S3 is a paper execution until the matching pull request is merged and the paper says so.** A draft is not a result.

## Map

| Step | What it is | Draft PR |
|---|---|---|
| S1 | Freeze the django-accounting pricing slice, stub Django, and put a golden-file oracle in place. | [PR #1](https://github.com/rossjwebb/zero-regression/pull/1) |
| Path-scrub | Replace leaked machine-local paths so CONFIG hashes change. | [PR #2](https://github.com/rossjwebb/zero-regression/pull/2) — parked. The paper and this repository still use the hashes on `master`. |
| CI + April 91.0 | Pull-request checks for the existing verifier (and the S1 oracle when present), plus a marker that the April 2026 figure of 91.0 is superseded. | [PR #3](https://github.com/rossjwebb/zero-regression/pull/3) |
| S2 | Defects4J Commons-CSV under PIT. | [PR #4](https://github.com/rossjwebb/zero-regression/pull/4) (pin and fail-closed runner); [PR #7](https://github.com/rossjwebb/zero-regression/pull/7) (CI). No mutation score is stored. |
| S3 | CardDemo COBOL. | [PR #5](https://github.com/rossjwebb/zero-regression/pull/5) (pin); [PR #6](https://github.com/rossjwebb/zero-regression/pull/6) (GnuCOBOL compile of the pinned program). Compile succeeded. That is not a green test job. |

## What this file is not

It does not merge any pull request. It does not change the mutation harness. It does not rewrite the fixture hashes on `master` or the hashes proposed in PR #2. It does not invent a mutation score.

`SUBJECTS.md` lists candidate Python subjects. Those candidates are not S1–S3.
