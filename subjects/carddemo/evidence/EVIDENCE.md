# S3 CardDemo posture evidence

This pack records what is checkable without a mutation score and without a POSTTRAN job. It is not a paper execution of S3.

Machine-readable copy: [`s3-posture.json`](s3-posture.json).

## Claims

- `mutation_score=not-stored`
- `paper_s3=unexecuted`
- `status=scaffolding+compile-runner-only`
- `posttran_job=not-run`
- `executed_job=false`

No mutation score is stored. The paper has not executed S3. This pack is scaffolding and compile-runner posture only. Compiling is not paper S3. The POSTTRAN job was not run.

## What is recorded

- Pin identities already used in `pins.toml`: aws-samples CardDemo `59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e`, slice POSTTRAN / `CBTRN02C`, GnuCOBOL 3.1.2.0 (`gnucobol3=3.1.2-5.1ubuntu1`, `.deb` URL and SHA-256 as in `pins.toml`).
- `check-pins.py` is the pin gate. On this tree it was run with Python 3.12.3 and exited 0. That exit is pin integrity, not a POSTTRAN job result.
- `run-cobol.sh` is fail-closed. Compile OK prints `S3 COMPILE OK` and the harness exits 2 (`S3 HARNESS EXIT 2`, `posttran_job=not-run`). A GnuCOBOL compile error prints `S3 COBC FAIL` and CI fails the job. This pack does not run POSTTRAN and does not store a `work/` receipt.

## What is not recorded

- No mutation score, no percentage, no CERTIFICATE.
- No `work/COMPILE` or compiled `CBTRN02C`. `work/` remains gitignored.
- No claim that a POSTTRAN job ran.
- No claim that paper S3 ran.
