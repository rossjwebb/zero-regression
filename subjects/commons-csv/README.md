# Commons-CSV (S2)

Public-replication subject: [Defects4J](https://github.com/rjust/defects4j) project **Csv**, which is [Apache Commons CSV](https://github.com/apache/commons-csv), under [PIT](https://pitest.org/) (Pitest).

The 2 September programme note names S2 as Defects4J Commons-CSV under PIT (floated, not started). There is no `W2-WO-S2` in this repository. This slice is the checkable pin, not a paper execution of S2.

Defects4J's own `mutation` command uses **Major**, not PIT. This subject uses PIT on the Defects4J Csv revision, which is what that note named.

Do not edit `legacy/`.

## Pins

| Field | Value |
|---|---|
| Defects4J | [v3.0.1](https://github.com/rjust/defects4j/releases/tag/v3.0.1) `6d54320e0db5a357f9ab38a8e4d2e5aead7e1c09` |
| Project / version | Csv-1f (fixed side of bug 1) |
| Commons-CSV | `de1838ea067f3fbc4c7c21b9eeae077c739ecb73` (27 March 2012, CSV-75) |
| Buggy pair (not the working tree) | `0833f45bffd40f44ba6f294d84e9bac8a9ba0a37` |
| Issue | [CSV-75](https://issues.apache.org/jira/browse/CSV-75) |
| Modified class | `org.apache.commons.csv.ExtendedBufferedReader` |
| Licence | Apache-2.0 (`legacy/LICENSE.txt`) |
| PIT | Pitest 1.15.3 command-line JARs, named mutator group **DEFAULTS** (not STRONGER) |
| JDK | Eclipse Temurin 11.0.32.1+1 (PIT 1.15.3 / Java 11+). Subject bytecode is `javac --release 8`. |

Hashes for every vendored file and every JAR are in `pins.toml`. They were written from fetched artifacts.

## Layout

- `legacy/` — bit-identical snapshot of the Csv-1f package and the tests listed in `pins.toml`
- `pins/` — Defects4J v3.0.1 `active-bugs.csv` header plus the Csv-1 row, and `modified_classes/1.src`
- `check-pins.py` — hash and metadata gate
- `run-pit.sh` — compile, run the green JUnit classes, then PIT; fail closed
- `evidence/` — live fail-closed PIT receipt plus pin/runner posture. No mutation score. Not paper S2. See `evidence/EVIDENCE.md`.
- `record-pit-receipt.py` — write a score-free receipt from `work/` (never copies HTML or `pit.log`)
- `check-s2-pit.py` — honesty gate; `--require-live` is fail-closed if the work tree is missing or the judge fails

PIT target: `ExtendedBufferedReader` only (161 source lines at this pin). The rest of the package is compiled so the green tests can run; it is `unverified_scope`.

## Green tests, and one red upstream test

At Csv-1f these classes pass:

- `CSVParserTest` (Defects4J trigger class, including `testGetLineNumberWithCR`)
- `CSVLexerTest`
- `CSVPrinterTest`
- `CSVFormatTest`

`ExtendedBufferedReaderTest` is still red on this fixed revision. The file itself contains CSV-75 TODOs and pre-fix expected line numbers. It is vendored for pin identity and is **not** a gate.

## How to run

From the repository root, with Python 3.12.3. Do not put Java 21 on `PATH` and expect the runner to use it. The script fetches the pinned Temurin 11 tarball (hash in `pins.toml`) unless `S2_JAVA_HOME` is already that same 11.0.32.1 release.

```bash
python3.12 subjects/commons-csv/check-pins.py
python3.12 -m unittest tests.test_commons_csv_pins tests.test_commons_csv_toolchain tests.test_commons_csv_pit_evidence
./subjects/commons-csv/run-pit.sh
python3.12 subjects/commons-csv/check-s2-pit.py --require-live
```

`run-pit.sh` downloads the pinned JDK 11 and JARs into `subjects/commons-csv/work/`, checks SHA-256, compiles with that JDK's `javac --release 8`, checks the classfile major version is 52 (Java 8), runs the four green test classes on JDK 11, then invokes PIT on the same JDK with `--mutators DEFAULTS` and explicit target/exclude class filters.

PIT minions get a 256m heap and a pinned timeout so one mutant TIMED_OUT or OOM does not crash the parent process. That isolation is **not** a success: the log judge still exits 2 if any mutant is TIMED_OUT, MEMORY_ERROR, or RUN_ERROR, or if a minion exits abnormally. No partial score is written.

The script exits 2 if any step fails (wrong JDK, download failure, hash mismatch, non-Java-8 classfiles, red green-suite, PIT process failure, isolated edge case, or no HTML report).

Maven is not required. Defects4J Major is not used.

The HTML report is written to `subjects/commons-csv/work/pit-reports/index.html`. That path is gitignored. This repository does not store a mutation score for S2.

The committed pack under `evidence/` records pin identities, that `check-pins.py` is the gate, that `run-pit.sh` is fail-closed, and that a live PIT process was executed on this slice. It states `mutation_score=not-stored`, `paper_s2=unexecuted`, and `status=live-pit-executed`. The receipt stores process facts only (exit 0, judge clean, HTML present and gitignored). It does not store a kill-rate percentage. It is not a paper execution of S2.

S2 status: the PR #12 pack was scaffolding+runner-only. This slice ran the pinned PIT runner live and kept the score out of the repository. CI always re-runs that same fail-closed path (`check-s2-pit.py --require-live`). A missing work tree or a TIMED_OUT / MEMORY_ERROR / RUN_ERROR mutant is fail-closed, not a skip-as-pass. Operator has not allowed a mutation number; none is stored.

## Out of scope

- No paper, LaTeX, or citation work
- No claim that the paper already executed S2
- No mutmut five-stage run on this subject. `zr certify subjects/commons-csv` is the score-free PIT evidence gate (`mutation_score=not-stored`), not a kill-rate certificate
- No rewrite of the Python mutation harness
