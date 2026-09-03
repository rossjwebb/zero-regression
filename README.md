# Zero-Regression

## What this is

A deterministic certification harness. A completed run issues a three-line certificate:

- **COVERAGE** — the observed region, as measured
- **KILL RATE** — killed/seeded in that region, with survivor classes
- **UNVERIFIED** — the declared unobserved region

This repository makes no Generator, Adjudicator, or Executor calls.

Unexecuted replication steps (S1–S3) and the draft pull requests that hold them are listed in [PROGRAMME.md](PROGRAMME.md). None of those steps is a paper execution until merged and the paper says so.

## How to run

From a fresh clone, with Python 3.12.3 on `PATH`:

```bash
python3.12 -m venv .venv && . .venv/bin/activate && python -m pip install -r requirements-certification.txt
./certify.sh subjects/accounting-service
./verify.py subjects/accounting-service/evidence/run-*/evidence.jsonl
```

The S1 django-accounting subject is pinned at `2e61776a653e719a4c15578ab385603a6066c2b6`. From a fresh clone:

```bash
python3.12 subjects/django-accounting/oracle.py
```

That command replays recorded traces. CI on the S1 branch requires stdout to be exactly `ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only`. `cases=19` fails. This is not a proof of accounting correctness and not a paper execution of S1. See `subjects/django-accounting/ORACLE.md`.

S2 is Defects4J Commons-CSV under PIT. The pin is Csv-1f (`de1838ea067f3fbc4c7c21b9eeae077c739ecb73`). This repository does not record a mutation score for S2 and does not claim that the paper already executed it.

```bash
python3.12 subjects/commons-csv/check-pins.py
./subjects/commons-csv/run-pit.sh
```

S3 is public CardDemo COBOL (batch POSTTRAN / `CBTRN02C`). The pin is `aws-samples/aws-mainframe-modernization-carddemo` `59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e`. There are no legacy tests. This repository does not record a mutation score for S3 and does not claim that the paper already executed it.

```bash
python3.12 subjects/carddemo/check-pins.py
./subjects/carddemo/run-cobol.sh
```

`check-pins.py` exits 0 when the pin holds. GnuCOBOL is pinned to Ubuntu `gnucobol3=3.1.2-5.1ubuntu1` (`cobc` 3.1.2.0): the runner fetches that `.deb`, hash-checks it, and refuses a different PATH `cobc`. With the pin present, `run-cobol.sh` compiles `CBTRN02C` (`cobc_status=0`) and then the harness exits 2. That exit 2 means `posttran_job=not-run`, not a GnuCOBOL error. Do not treat it as a `cobc` failure, and do not change it to exit 0. A real GnuCOBOL error prints `S3 COBC FAIL` and CI fails the job. S3 remains unexecuted: no legacy tests, no claimed CardDemo run, no score.

CI on this branch always runs `.github/workflows/s3-carddemo-compile.yml`. There is no skip path. A missing runner fails. A `cobc` compile error fails the job. Success must still be `S3 COMPILE OK`, harness exit 2, `posttran_job=not-run`. That is not paper S3.

## Evidence-chain schema

The log is an append-only sequence of JSON records. Every record carries: `seq` (monotonic integer); `ts` (UTC timestamp); `type` (one of `CONFIG`, `BASELINE`, `MUTANT_RESULT`, `TRIAGE`, `OVERRIDE`, `CERTIFICATE`, `COST`); `payload` (type-specific body); `prev_hash` (the SHA-256 fingerprint of the preceding record's canonical serialisation); `hash` (the SHA-256 fingerprint of this record's canonical serialisation, including `prev_hash`). `COST` records attributable spend from an external generation run: role, token count, spend in USD, and an immutable reference.

## How to verify a chain without trusting the issuer

Given the log: (1) recompute every record's `hash` from its canonical serialisation and confirm it matches; (2) confirm every `prev_hash` equals the predecessor's `hash` — any break locates tampering to the exact row; (3) confirm the `CERTIFICATE` record's three lines are derivable from the `MUTANT_RESULT` and `TRIAGE` records alone — the certificate must add no information the chain does not contain.

```bash
./verify.py path/to/evidence.jsonl
```

Exit 0 means the chain holds. On failure the first broken `seq` is printed. Steps 1–3 need no trust in the issuer and no execution environment.

Three executed `accounting-service` chains are kept:

- `fixtures/accounting-service/` — post-approval chain. OVERRIDE records were written after the principal signed the four equivalents. `CONFIG` hash `8ecb042134c8fb756f2e3686489681b96c26b9f111b6b84b614c72f95729b455`.
- `fixtures/accounting-service/superseded/publish-4/` — same remediation, but its OVERRIDE records predate that approval; superseded, not deleted. `CONFIG` hash `059f40e476d9e8d1d5be65e241e28acc334f110b7523d5bf3a562e4b2117e97e`.
- `fixtures/accounting-service/pre-remediation/` — the executed chain that found the two gaps. `CONFIG` hash `1c206c919541b9d95637837e60570cd9ca466c2450cb4a6c2ee7f74e2f66581e`.

An earlier April 2026 figure of 91.0% / 279 mutants is superseded. See `APRIL-2026-SUPERSEDED.md`. Do not cite that figure.

Pull-request checks re-run the fixture verifier and, when the draft PR #1 runner is present, the django-accounting replay oracle. A match is a replay of 27 recorded traces, not a proof of accounting correctness and not a paper S1 result.

```bash
python3.12 ./verify.py fixtures/accounting-service/evidence.jsonl
python3.12 ./verify.py fixtures/accounting-service/pre-remediation/evidence.jsonl
python3.12 ./verify.py fixtures/accounting-service/superseded/publish-4/evidence.jsonl
python3.12 subjects/django-accounting/oracle.py
```

The oracle must print `ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only` and exit 0. Any other line fails the check.
