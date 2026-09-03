# CardDemo (S3)

Public-replication subject: the public [CardDemo](https://github.com/aws-samples/aws-mainframe-modernization-carddemo) COBOL application (AWS Mainframe Modernization CardDemo). It is the IBM-style COBOL/CICS/JCL credit-card sample. There is no separate IBM GitHub CardDemo pin; this is the named public CardDemo.

The 2 September programme note names S3 as **CardDemo COBOL, no legacy tests** (floated, not started). There is no `W2-WO-S3` in this repository. This slice is the checkable pin and a fail-closed compile runner. It is **not** a paper execution of S3.

Do not create `legacy/` or `golden/`. Do not invent tests and call them legacy.

## Pins

| Field | Value |
|---|---|
| Upstream | https://github.com/aws-samples/aws-mainframe-modernization-carddemo |
| Pin | `59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e` (16 October 2025) |
| Licence | Apache-2.0 (`batch/LICENSE`) |
| Slice | POSTTRAN batch job, program `CBTRN02C` (731 physical lines) plus the five `COPY` books it uses |
| Tree at pin | 329 paths, 44 COBOL programs (`pins/carddemo-59cc6c2f.ls-tree.txt`) |
| Legacy tests | **none** |

Hashes for every vendored file were written from the fetched tree. The tree listing and the no-legacy-tests scan were written from `git ls-tree` at that commit.

The three paths whose names contain `test` are sample IDCAMS/SORT JCL (`samples/jcl/REPRTEST.jcl`, `samples/jcl/SORTTEST.jcl`) and a marker file (`scripts/markers/REPRTEST`). They are not COBOL unit tests and are not part of this slice.

## Layout

- `batch/` — bit-identical snapshot of the POSTTRAN program, its copybooks, the POSTTRAN JCL, and the upstream licence/notice
- `pins/` — full `ls-tree` at the pin, and the no-legacy-tests scan
- `check-pins.py` — hash and metadata gate
- `run-cobol.sh` — compile CBTRN02C with `cobc` when present; fail-closed if compile fails or if there are no tests; never records a score

There is no `legacy/` directory. S1 uses `legacy/` for a Python oracle; S3 does not, because CardDemo has no legacy tests.

## How to run

From the repository root, with Python 3.12.3:

```bash
python3.12 subjects/carddemo/check-pins.py
python3.12 -m unittest tests.test_carddemo_pins
./subjects/carddemo/run-cobol.sh
```

`check-pins.py` should print `S3 PIN OK` and exit 0.

`run-cobol.sh` is fail-closed. It exits 2 if:

1. the pin check fails, or
2. no COBOL compiler is on `PATH` (looks for `cobc`, `cob`, `cob2`), or
3. the compiler is present but `CBTRN02C` does not compile, or
4. the compiler succeeds — there is still no test suite, so the script refuses to report a green run.

## What compiles, and what still cannot

GnuCOBOL is installable on Ubuntu 24.04 and on GitHub Actions `ubuntu-latest` (jammy and noble both ship the `gnucobol` metapackage):

```bash
sudo apt-get update
sudo apt-get install -y gnucobol
cobc --version
```

Observed on Ubuntu 24.04.4: `cobc (GnuCOBOL) 3.1.2.0` from `gnucobol3=3.1.2-5.1ubuntu1`.

With that compiler, `run-cobol.sh` **does compile** the pinned POSTTRAN program `CBTRN02C` (`cobc -std=ibm -x`) plus its five `COPY` books. That is a compile only.

The following still cannot happen on this image, and the runner does not pretend otherwise:

- IBM Enterprise COBOL (`cob2`) is absent
- There is no legacy test suite, so the script still exits 2 after a successful compile
- No mutation score is recorded
- The binary is not a POSTTRAN job run: there is no `DALYTRAN` sequential file, no VSAM/INDEXED data, and no IBM Language Environment `CEE3ABD`
- Online CICS programs, remaining batch programs, JCL, and EBCDIC data are outside this slice

The script does not write a mutation score. This repository does not store a mutation score for S3.

## Out of scope

- No paper, LaTeX, or citation work
- No claim that the paper already executed S3
- No `certify.sh` / mutmut run on this subject
- No rewrite of the Python mutation harness
- No invented COBOL tests
- No merge of PR #1, PR #2, PR #3, or PR #4
