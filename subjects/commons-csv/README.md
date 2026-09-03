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
| PIT | Pitest 1.15.3 command-line JARs (JUnit 4; no Maven plugin) |

Hashes for every vendored file and every JAR are in `pins.toml`. They were written from fetched artifacts.

## Layout

- `legacy/` — bit-identical snapshot of the Csv-1f package and the tests listed in `pins.toml`
- `pins/` — Defects4J v3.0.1 `active-bugs.csv` header plus the Csv-1 row, and `modified_classes/1.src`
- `check-pins.py` — hash and metadata gate
- `run-pit.sh` — compile, run the green JUnit classes, then PIT; fail closed

PIT target: `ExtendedBufferedReader` only (161 source lines at this pin). The rest of the package is compiled so the green tests can run; it is `unverified_scope`.

## Green tests, and one red upstream test

At Csv-1f these classes pass:

- `CSVParserTest` (Defects4J trigger class, including `testGetLineNumberWithCR`)
- `CSVLexerTest`
- `CSVPrinterTest`
- `CSVFormatTest`

`ExtendedBufferedReaderTest` is still red on this fixed revision. The file itself contains CSV-75 TODOs and pre-fix expected line numbers. It is vendored for pin identity and is **not** a gate.

## How to run

From the repository root, with Python 3.12.3 and a JDK that can run `javac --release 8`:

```bash
python3.12 subjects/commons-csv/check-pins.py
python3.12 -m unittest tests.test_commons_csv_pins
./subjects/commons-csv/run-pit.sh
```

`run-pit.sh` downloads the pinned JARs into `subjects/commons-csv/work/lib/`, checks their SHA-256, compiles the snapshot, runs the four green test classes, then invokes PIT. It exits 2 if any step fails (missing `javac`, download failure, hash mismatch, red green-suite, or no PIT report).

Maven is not required. This VM image has OpenJDK and no Maven; the command-line JARs are still PIT. Defects4J Major is not used.

The HTML report is written to `subjects/commons-csv/work/pit-reports/index.html`. That path is gitignored. This repository does not store a mutation score for S2.

## Out of scope

- No paper, LaTeX, or citation work
- No claim that the paper already executed S2
- No `certify.sh` / mutmut run on this subject
- No rewrite of the Python mutation harness
