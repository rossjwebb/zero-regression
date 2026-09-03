# Zero-Regression

## What this is

A deterministic certification harness. A completed run issues a three-line certificate:

- **COVERAGE** — the observed region, as measured
- **KILL RATE** — killed/seeded in that region, with survivor classes
- **UNVERIFIED** — the declared unobserved region

This repository makes no Generator, Adjudicator, or Executor calls.

## How to run

From a fresh clone, with Python 3.12.3 on `PATH`:

```bash
python3.12 -m venv .venv && . .venv/bin/activate && python -m pip install -r requirements-certification.txt
./certify.sh subjects/accounting-service
./verify.py subjects/accounting-service/evidence/run-*/evidence.jsonl
```

S3 is public CardDemo COBOL (batch POSTTRAN / `CBTRN02C`). The pin is `aws-samples/aws-mainframe-modernization-carddemo` `59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e`. There are no legacy tests. This repository does not record a mutation score for S3 and does not claim that the paper already executed it.

```bash
python3.12 subjects/carddemo/check-pins.py
./subjects/carddemo/run-cobol.sh
```

`check-pins.py` exits 0 when the pin holds. GnuCOBOL is pinned to Ubuntu `gnucobol3=3.1.2-5.1ubuntu1` (`cobc` 3.1.2.0): the runner fetches that `.deb`, hash-checks it, and refuses a different PATH `cobc`. With the pin present, `run-cobol.sh` compiles `CBTRN02C` and still exits 2. That is compile-only, not a green POSTTRAN job. S3 remains unexecuted: no legacy tests, no claimed CardDemo run, no score. If `cobc` is missing, the version mismatches, or compile fails, the script also exits 2.

## Evidence-chain schema

The log is an append-only sequence of JSON records. Every record carries: `seq` (monotonic integer); `ts` (UTC timestamp); `type` (one of `CONFIG`, `BASELINE`, `MUTANT_RESULT`, `TRIAGE`, `OVERRIDE`, `CERTIFICATE`, `COST`); `payload` (type-specific body); `prev_hash` (the SHA-256 fingerprint of the preceding record's canonical serialisation); `hash` (the SHA-256 fingerprint of this record's canonical serialisation, including `prev_hash`). `COST` records attributable spend from an external generation run: role, token count, spend in USD, and an immutable reference.

## How to verify a chain without trusting the issuer

Given the log: (1) recompute every record's `hash` from its canonical serialisation and confirm it matches; (2) confirm every `prev_hash` equals the predecessor's `hash` — any break locates tampering to the exact row; (3) confirm the `CERTIFICATE` record's three lines are derivable from the `MUTANT_RESULT` and `TRIAGE` records alone — the certificate must add no information the chain does not contain.

```bash
./verify.py path/to/evidence.jsonl
```

Exit 0 means the chain holds. On failure the first broken `seq` is printed. Steps 1–3 need no trust in the issuer and no execution environment.

Three executed `accounting-service` chains are kept:

- `fixtures/accounting-service/` — post-approval chain. OVERRIDE records were written after the principal signed the four equivalents. `CONFIG` hash `60df647fc89a72ea0627b9bf933482bea4e9259f53f6614c4b61c78590a8be06`.
- `fixtures/accounting-service/superseded/publish-4/` — same remediation, but its OVERRIDE records predate that approval; superseded, not deleted. `CONFIG` hash `eccc17cdcc1f82072451ef9a38a5555457b4d75aedf5112ab75d1c09f40b321b`.
- `fixtures/accounting-service/pre-remediation/` — the executed chain that found the two gaps. `CONFIG` hash `1c7f02cc4305fc0aae65bb6f1ed8d62aaeda67fa793c579004143717926a3afd`.
