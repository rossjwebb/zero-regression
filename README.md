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
