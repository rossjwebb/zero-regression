# Public-replication subject protocol

Each selected subject must be Python, permissively licensed, deterministic and green under its pinned checkout, and have no network dependency in its test suite. The certification scope must contain 150–600 executable source lines. Larger repositories are admissible only when the tested, configured source slice is independently runnable and its boundary is declared in `unverified_scope`.

Before selection, record the commit SHA, licence text, installation command, test command, source/test paths, offline-test evidence, and LOC count in the subject’s `zero-regression.toml` and `evidence/` folder. Do not certify a moving default branch. A green test suite is a precondition, not a result.

## Public-replication shortlist

| Public repository | Candidate slice | Fit note |
|---|---|---|
| [py-moneyed](https://github.com/py-moneyed/py-moneyed) | `src/moneyed/classes.py` plus directly exercised currency helpers | BSD-3-Clause money and currency primitives; a bounded arithmetic slice is appropriate for the target size. |
| [stockholm](https://github.com/kalaspuff/stockholm) | one `Money`/rounding module and its unit tests | MIT monetary-value library with an explicitly advertised high-coverage unit-test posture. |
| [money](https://github.com/carlospalol/money) | core Money arithmetic module | MIT money-value implementation; pin an interpreter-compatible historical commit before running. |
| [fintech-ledger-engine](https://github.com/stephenvelasquez/fintech-ledger-engine) | transaction balancing and posting core | MIT double-entry ledger logic; configure the invariant-heavy core as the bounded subject. |
| [financial-health-calculator](https://github.com/engineerinvestor/financial-health-calculator) | one deterministic CEFR or withdrawal-calculation module | MIT project with pytest; exclude Monte Carlo and UI/API paths unless their determinism is established. |

The entries are candidates, not completed replications. At selection time, reject any whose selected checkout cannot run offline under the exact certification pins. Record that rejection in the evidence folder rather than silently replacing the subject.

## Selected: django-accounting

| Field | Record |
|---|---|
| Upstream | https://github.com/dulacp/django-accounting |
| Pin | `2e61776a653e719a4c15578ab385603a6066c2b6` (2 December 2017) |
| Licence | MIT (`subjects/django-accounting/legacy/LICENSE`) |
| Slice | `Price` and the collected-profits calculator (174 executable lines) |
| Offline evidence | Import stubs only (no Django ORM/SQL). `python3.12 subjects/django-accounting/oracle.py` replays 27 recorded traces against `golden/expected.json`. Stage C `check-discrimination.py` rejects known-bad probes and a golden-echo stub. Stage D `check-stage-d.py` evaluates produced rewrite candidates against that yardstick. That is not a proof of accounting correctness and not paper S1. |
| Test command | `python3.12 subjects/django-accounting/oracle.py` |
| Working tree | `subjects/django-accounting/` |

## Selected: Commons-CSV (S2)

The 2 September programme note names S2 as Defects4J Commons-CSV under PIT. That is Apache Commons CSV (Defects4J project `Csv`), mutated with Pitest, not with Defects4J Major. This is a pin and a reproduce script. It is not a paper execution of S2 and it does not record a mutation score.

| Field | Record |
|---|---|
| Defects4J | [v3.0.1](https://github.com/rjust/defects4j/releases/tag/v3.0.1) `6d54320e0db5a357f9ab38a8e4d2e5aead7e1c09` |
| Subject version | Csv-1f |
| Upstream | https://github.com/apache/commons-csv |
| Pin | `de1838ea067f3fbc4c7c21b9eeae077c739ecb73` (27 March 2012, CSV-75) |
| Licence | Apache-2.0 (`subjects/commons-csv/legacy/LICENSE.txt`) |
| Slice | `org.apache.commons.csv.ExtendedBufferedReader` (Defects4J modified class for Csv-1) |
| PIT | Pitest 1.15.3 command-line JARs, mutators DEFAULTS, JDK Temurin 11.0.32.1+1, subject `--release 8` |
| Test command | `python3.12 subjects/commons-csv/check-pins.py` then `./subjects/commons-csv/run-pit.sh` |
| Working tree | `subjects/commons-csv/` |

## Selected: CardDemo (S3)

The 2 September programme note names S3 as CardDemo COBOL, no legacy tests. The public CardDemo is AWS Mainframe Modernization CardDemo (IBM-style COBOL/CICS/JCL). This is a pin and a fail-closed compile script. Pinned GnuCOBOL `3.1.2.0` (Ubuntu `gnucobol3=3.1.2-5.1ubuntu1`) can compile `CBTRN02C`. That compile is not a paper execution of S3, not a green POSTTRAN job, and it does not record a mutation score. S3 remains unexecuted.

| Field | Record |
|---|---|
| Upstream | https://github.com/aws-samples/aws-mainframe-modernization-carddemo |
| Pin | `59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e` (16 October 2025) |
| Licence | Apache-2.0 (`subjects/carddemo/batch/LICENSE`) |
| Slice | POSTTRAN / `CBTRN02C` plus five `COPY` books |
| Legacy tests | none (no `tests/` tree; `test_paths = []`) |
| Test command | `python3.12 subjects/carddemo/check-pins.py` then `sudo apt-get install -y gnucobol3=3.1.2-5.1ubuntu1` then `./subjects/carddemo/run-cobol.sh` |
| Compiler pin | Ubuntu noble `gnucobol3=3.1.2-5.1ubuntu1`; `.deb` URL + SHA-256 in `pins.toml`; `/usr/bin/cobc` hash and `cobc --version` must match; PATH `cobc` may not mix |
| Compile | pinned `cobc` 3.1.2.0 compiles `CBTRN02C`; not a POSTTRAN job; no tests; runner exits 2 |
| Working tree | `subjects/carddemo/` |
