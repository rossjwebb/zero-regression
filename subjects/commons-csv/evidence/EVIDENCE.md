# S2 Commons-CSV posture evidence

This pack records what is checkable without a mutation score. It is not a paper execution of S2.

Machine-readable copy: [`s2-posture.json`](s2-posture.json).

## Claims

- `mutation_score=not-stored`
- `paper_s2=unexecuted`
- `status=scaffolding+runner-only`

No mutation score is stored. The paper has not executed S2. This pack is scaffolding and runner posture only.

## What is recorded

- Pin identities already used in `pins.toml`: Defects4J v3.0.1 `6d54320e0db5a357f9ab38a8e4d2e5aead7e1c09`, Commons-CSV Csv-1f `de1838ea067f3fbc4c7c21b9eeae077c739ecb73`, PIT 1.15.3 named mutator group DEFAULTS, Temurin 11.0.32.1+1 (`sha256` as in `pins.toml`).
- `check-pins.py` is the pin gate. On this tree it was run with Python 3.12.3 and exited 0. That exit is pin integrity, not a PIT result.
- `run-pit.sh` is fail-closed. `toolchain.py:judge_pit_log` treats TIMED_OUT, MEMORY_ERROR, and RUN_ERROR as failures; the runner exits non-zero. This pack does not run PIT and does not store a report.

## What is not recorded

- No mutation score, no percentage, no CERTIFICATE.
- No PIT HTML. `work/pit-reports/` remains gitignored.
- No claim that paper S2 ran.
