# S3 CardDemo posture evidence

This pack records a live GnuCOBOL POSTTRAN fixture run without a mutation
score and without a paper S3 claim. It is not a paper execution of S3.

Machine-readable copies: [`s3-posture.json`](s3-posture.json),
[`job-receipt.json`](job-receipt.json).

## Claims

- `mutation_score=not-stored`
- `paper_s3=unexecuted`
- `status=gnucobol-posttran-fixture-run`
- `posttran_job=run`
- `runtime=gnucobol-indexed-bdb-fixture`
- `executed_job=true`
- `ibm_vsam=false`
- `ibm_cics=false`

No mutation score is stored. The paper has not executed S3. Compiling is still not paper S3. The job that ran is a GnuCOBOL INDEXED/BDB fixture
path, not IBM VSAM, not CICS, and not IBM Language Environment.

## What ran

On Python 3.12.3 this slice ran `./subjects/carddemo/run-posttran.sh`
after the pinned Ubuntu `gnucobol3=3.1.2-5.1ubuntu1` (`cobc` 3.1.2.0)
compiled `CBTRN02C`. The compile-only runner `run-cobol.sh` still prints
`S3 COMPILE OK` and exits 2 (`S3 HARNESS EXIT 2`, compile-runner
`posttran_job=not-run`). That compile is not the job.

`run-posttran.sh` then compiled `runtime/seed-indexed.cbl` and the
`CEE3ABD` stub, wrote synthetic sequential `DALYTRAN` plus GnuCOBOL
INDEXED `XREFFILE` / `ACCTFILE` / `TCATBALF` (Berkeley DB handler),
assigned those files through `DD_*` environment names matching the
POSTTRAN JCL DDs, and executed `work/CBTRN02C`.

The program displayed `START OF EXECUTION OF PROGRAM CBTRN02C`,
`TRANSACTIONS PROCESSED :000000002`, `TRANSACTIONS REJECTED  :000000001`,
and `END OF EXECUTION OF PROGRAM CBTRN02C`. It set `RETURN-CODE` 4
because rejects were greater than zero. That is the program's own rule.
A live `work/POSTTRAN` receipt is gitignored. This pack does not store
that file body or the timestamped `TRANFILE` bytes.

`check-pins.py` is still the pin gate. On this tree it was run with
Python 3.12.3 and exited 0. That exit is pin integrity, not a paper
result.

## What is not recorded

- No mutation score, no percentage, no CERTIFICATE.
- No `work/COMPILE`, `work/POSTTRAN`, or compiled `CBTRN02C`. `work/`
  remains gitignored.
- No IBM VSAM/KSDS files.
- No CICS transaction.
- No IBM Language Environment `CEE3ABD` (the linked module is a harness
  stub).
- No claim that paper S3 ran.
